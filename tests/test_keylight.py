import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import ae_comp  # noqa: E402
import keylight  # noqa: E402

IMAGING = all(importlib.util.find_spec(name) for name in ("numpy", "cv2"))
EDGE, CORE = "Keylight Edge", "Keylight Core"


def match(name):
    return f"{ae_comp.KEYLIGHT}-{ae_comp.KEYLIGHT_PARAMS[name]}"


class KeylightCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve() / "work"
        self.shot_dir = self.work / "shot01"

    def sequence(self, folder, count, name="frame_", digits=4, suffix=".png"):
        folder.mkdir(parents=True, exist_ok=True)
        for number in range(1, count + 1):
            (folder / f"{name}{number:0{digits}d}{suffix}").write_bytes(b"")
        return folder

    def contract(self, **keylight_settings):
        self.shot_dir.mkdir(parents=True, exist_ok=True)
        (self.shot_dir / "shot.json").write_text(json.dumps({"fps": 24, "keylight": keylight_settings}))

    def job(self, argv):
        return ae_comp.build_job(ae_comp.parse_args(argv))


class KeylightPresetTests(KeylightCase):
    def argv(self, *extra):
        return ["keylight", "--shot", "shot01", "--work", str(self.work), "--no-dialogs", *extra]

    def test_plate_keyed_over_background_with_core_pass_off(self):
        self.sequence(self.shot_dir / "frames", 8)
        background = self.shot_dir / "bg.png"
        background.write_bytes(b"")
        self.contract(screen_colour=[0.3, 0.6, 0.35], garbage=[[0, 0], [100, 0], [100, 50]])
        job = self.job(self.argv("--background", str(background)))
        self.assertEqual([layer["role"] for layer in job["layers"]], ["background", "plate"])
        self.assertEqual(job["plate_index"], 1)
        effects = {e["name"]: e for e in job["keylight"]["effects"]}
        self.assertFalse(effects[CORE]["enabled"])
        self.assertTrue(effects[EDGE]["enabled"])
        edge = effects[EDGE]["params"]
        self.assertEqual(edge[match("screen_colour")], [0.3, 0.6, 0.35, 1.0])
        self.assertEqual(edge[match("screen_balance")], 50)
        self.assertEqual(edge[match("source_alpha")], 1)  # the plate's own alpha must not become an inside mask
        # The garbage polygon becomes a track matte layer after Keylight, not Keylight's Outside Mask.
        self.assertNotIn(match("outside_mask"), edge)
        self.assertEqual(job["keylight"]["garbage"], [[0.0, 0.0], [100.0, 0.0], [100.0, 50.0]])
        self.assertEqual(effects[CORE]["params"][match("view")], ae_comp.VIEW["intermediate"])
        self.assertLess(effects[CORE]["params"][match("shrink_grow")], 0)
        # Spill suppression on, Ultra, keyed on the pure screen hue rather than the greyer measured colour.
        self.assertTrue(effects["Spill"]["enabled"])
        self.assertEqual(effects["Spill"]["params"], {"ADBE Spill2-0001": 2, "ADBE Spill2-0003": [0.0, 1.0, 0.0, 1.0]})

    def test_blue_screen_balance_and_no_garbage(self):
        self.sequence(self.shot_dir / "frames", 4)
        self.contract()
        job = self.job(self.argv("--screen-colour", "20,40,200"))
        edge = next(e for e in job["keylight"]["effects"] if e["name"] == EDGE)["params"]
        self.assertEqual(edge[match("screen_balance")], 95)
        self.assertIsNone(job["keylight"]["garbage"])
        spill = next(e for e in job["keylight"]["effects"] if e["name"] == "Spill")["params"]
        self.assertEqual(spill["ADBE Spill2-0003"], [0.0, 0.0, 1.0, 1.0])

    def test_needs_a_screen_colour(self):
        self.sequence(self.shot_dir / "frames", 4)
        self.contract()
        with self.assertRaisesRegex(ae_comp.CompError, "screen-colour"):
            self.job(self.argv())

    def test_keying_preset_still_puts_the_plate_first(self):
        self.sequence(self.shot_dir / "frames", 6)
        key = self.sequence(self.shot_dir / "key", 6, name="key.")
        job = self.job(["keying", "--shot", "shot01", "--work", str(self.work), "--fps", "24", "--key", str(key)])
        self.assertEqual(job["plate_index"], 0)
        self.assertIsNone(job["keylight"])
        self.assertEqual(job["project"]["bits_per_channel"], 16)

    def test_exr_key_gets_a_linear_srgb_project(self):
        self.sequence(self.shot_dir / "frames", 6)
        key = self.sequence(self.shot_dir / "key", 6, name="cutout_", digits=6, suffix=".exr")
        job = self.job(["keying", "--shot", "shot01", "--work", str(self.work), "--fps", "24", "--key", str(key)])
        self.assertEqual(job["project"], ae_comp.LINEAR_SRGB_32)

    def test_core_erosion_scales_with_plate_height(self):
        frames = self.shot_dir / "frames"
        frames.mkdir(parents=True)
        header = b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR" + (3840).to_bytes(4, "big") + (2160).to_bytes(4, "big")
        for n in range(1, 4):
            (frames / f"p_{n:04d}.png").write_bytes(header + b"\x00" * 8)
        self.contract(screen_colour=[0.3, 0.6, 0.3])
        job = self.job(self.argv())
        core = next(e for e in job["keylight"]["effects"] if e["name"] == CORE)["params"]
        self.assertEqual(core[match("shrink_grow")], -9)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_generated_build_jsx_parses(self):
        self.sequence(self.shot_dir / "frames", 4)
        self.contract(screen_colour=[0.3, 0.6, 0.35], garbage=[[0, 0], [10, 0], [10, 10]])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ae_comp.main(self.argv()), 0)
        script = self.shot_dir / "ae" / "check.js"
        shutil.copyfile(self.shot_dir / "ae" / "build_comp.jsx", script)
        result = subprocess.run([shutil.which("node"), "--check", str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class RoundTests(KeylightCase):
    def build_receipt(self, background=True):
        layers = [{"name": "Plate"}] + ([{"name": "Background"}] if background else [])
        receipt = {"status": "ok", "comp": {"name": "shot01_keylight", "fps": 24, "frames": 48},
                   "layers": layers, "keylight": {"effects": []}}
        (self.shot_dir / "ae").mkdir(parents=True, exist_ok=True)
        (self.shot_dir / "ae" / "build_comp.result.json").write_text(json.dumps(receipt))

    def args(self, *extra):
        return keylight.parse_args(["round", "--shot", "shot01", "--work", str(self.work), *extra])

    def test_parse_set(self):
        changes = keylight.parse_set(["edge.clip_black=20", "edge.screen_colour=92,158,94", "spill.enabled=on",
                                      "cleaner.edge_radius=4"])
        self.assertEqual(changes[EDGE]["params"][match("clip_black")], 20.0)
        self.assertAlmostEqual(changes[EDGE]["params"][match("screen_colour")][1], 158 / 255)
        self.assertTrue(changes["Spill"]["enabled"])
        self.assertEqual(changes["Key Cleaner"]["params"]["ADBE KeyCleaner-0006"], 4.0)
        for bad in (["edge.clip_black"], ["matte.clip_black=1"], ["edge.nonsense=1"], ["spill.enabled=yes"]):
            with self.assertRaises(ae_comp.CompError):
                keylight.parse_set(bad)

    def test_core_on_switches_the_edge_source_alpha(self):
        self.contract(planned_from_frames=[0, 24, 47])
        self.build_receipt()
        job, out_dir = keylight.round_job(self.args("--core", "on", "--set", "core.shrink_grow=-4"))
        changes = {c["effect"]: c for c in job["changes"]}
        self.assertTrue(changes[CORE]["enabled"])
        self.assertEqual(changes[CORE]["params"][match("shrink_grow")], -4.0)
        self.assertEqual(changes[EDGE]["params"][match("source_alpha")], 2)
        self.assertEqual(job["frames"], [0, 24, 47])
        self.assertEqual([v["name"] for v in job["views"]], ["status", "final", "comp", "core"])
        self.assertEqual(out_dir.name, "round_01")
        self.assertEqual(keylight.round_job(self.args())[1].name, "round_02")

    def test_round_needs_a_successful_keylight_build(self):
        self.contract()
        with self.assertRaisesRegex(ae_comp.CompError, "build receipt"):
            keylight.round_job(self.args())
        self.build_receipt()
        with self.assertRaisesRegex(ae_comp.CompError, "within"):
            keylight.round_job(self.args("--frames", "0,48"))

    def test_round_script(self):
        self.contract()
        self.build_receipt(background=False)
        job, out_dir = keylight.round_job(self.args("--set", "edge.clip_white=80"))
        self.assertNotIn("comp", [v["name"] for v in job["views"]])
        jsx = keylight.write_round(job, out_dir)
        text = jsx.read_text(encoding="ascii")
        self.assertIn(job["job_id"], text)
        template = keylight.TEMPLATE.read_text(encoding="ascii")
        for word in ("project.save", "project.close", "renderQueue", "app.quit", "alert("):
            self.assertNotIn(word, template)
        if shutil.which("node"):
            script = out_dir / "check.js"
            shutil.copyfile(jsx, script)
            result = subprocess.run([shutil.which("node"), "--check", str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(IMAGING, "NumPy and OpenCV not installed")
class MeasureTests(KeylightCase):
    """Synthetic plate: green screen, black flags on both sides, a grey subject in the middle."""

    def plate(self, h=120, w=200):
        import numpy as np
        image = np.zeros((h, w, 3), np.float32)
        image[:, 30:170] = (0.25, 0.6, 0.3)
        image[40:100, 80:120] = (0.4, 0.4, 0.42)
        return image

    def test_metrics(self):
        import numpy as np
        plate = self.plate()
        keep = keylight.keep_mask(plate.shape[:2], [[34, 0], [166, 0], [166, 119], [34, 119]])
        alpha = np.zeros(plate.shape[:2], np.float32)
        alpha[40:100, 80:120] = 1
        good = keylight.frame_metrics(plate, alpha, keep, "green", (0.25, 0.6, 0.3))
        self.assertEqual((good["bg_leak"], good["garbage_leak"], good["core_holes"]), (0, 0, 0))
        leaky = alpha.copy()
        leaky[5:15, 40:60] = 0.2       # grey screen
        leaky[50:60, 95:100] = 0.5     # see-through subject
        leaky[:, :20] = 1              # a flag that survived
        bad = keylight.frame_metrics(plate, leaky, keep, "green", (0.25, 0.6, 0.3))
        self.assertGreater(bad["bg_leak"], keylight.GATE["bg_leak"])
        self.assertGreater(bad["core_holes"], keylight.GATE["core_holes"])
        self.assertGreater(bad["garbage_leak"], keylight.GATE["garbage_leak"])

    def test_spill_share(self):
        import numpy as np
        plate = self.plate()
        keep = keylight.keep_mask(plate.shape[:2], None)
        alpha = np.zeros(plate.shape[:2], np.float32)
        alpha[40:100, 80:120] = 1
        alpha[40:100, 78:80] = 0.5     # soft edge
        keyed = np.repeat(np.float32([0.4, 0.4, 0.42])[None, None], 120 * 200, 0).reshape(120, 200, 3)
        clean = keylight.frame_metrics(plate, alpha, keep, "green", (0.25, 0.6, 0.3), keyed)
        self.assertEqual((clean["spill_edge"], clean["spill_solid"]), (0, 0))
        keyed[40:100, 78:80] = (0.3, 0.5, 0.3)     # green cast left in the edge
        keyed[60:62, 100:102] = (0.0, 0.02, 0.0)   # near black: noise, not spill
        cast = keylight.frame_metrics(plate, alpha, keep, "green", (0.25, 0.6, 0.3), keyed)
        self.assertEqual((cast["spill_edge"], cast["spill_solid"]), (1.0, 0.0))
        self.assertIsNone(keylight.frame_metrics(plate, alpha, keep, "green", (0.25, 0.6, 0.3))["spill_edge"])

    def test_plan_finds_colour_and_leaves_the_flags_out(self):
        import cv2
        import numpy as np
        frames = self.shot_dir / "frames"
        frames.mkdir(parents=True)
        for n in range(1, 4):
            image = self.plate()
            cv2.imwrite(str(frames / f"plate_{n:04d}.png"), (image[..., ::-1] * 65535).astype(np.uint16))
        args = keylight.parse_args(["plan", "--shot", "shot01", "--work", str(self.work)])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(keylight.plan(args), 0)
        settings = json.loads((self.shot_dir / "shot.json").read_text())["keylight"]
        self.assertEqual(settings["screen"], "green")
        self.assertTrue(np.allclose(settings["screen_colour"], (0.25, 0.6, 0.3), atol=0.01))
        xs = [x for x, _ in settings["garbage"]]
        self.assertGreaterEqual(min(xs), 30)
        self.assertLessEqual(max(xs), 170)
        self.assertTrue((self.shot_dir / "keylight" / "plan.png").exists())


if __name__ == "__main__":
    unittest.main()
