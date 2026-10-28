import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import ae_comp  # noqa: E402

PLATE = ae_comp.LAYERS[0]
RESULTS = ae_comp.LAYERS[1:]


def job_from_jsx(text):
    start = text.index("var job = ") + len("var job = ")
    return json.loads(text[start:text.index(";\n", start)])


class AeCompTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve() / "work"

    def sequence(self, folder, count, name="frame_", digits=4, first=1, suffix=".png"):
        folder.mkdir(parents=True, exist_ok=True)
        for number in range(first, first + count):
            (folder / f"{name}{number:0{digits}d}{suffix}").write_bytes(b"")
        return folder

    def shot(self, shot="shot01", plate_frames=10, result_frames=6):
        shot_dir = self.work / shot
        self.sequence(shot_dir / PLATE["default"], plate_frames)
        argv = ["--shot", shot, "--work", str(self.work), "--fps", "30000/1001", "--no-dialogs"]
        for spec in RESULTS:
            folder = self.sequence(shot_dir / "results" / spec["role"], result_frames, name=f"{spec['role']}.")
            argv += [f"--{spec['role']}", str(folder)]
        return shot_dir, argv

    def generate(self, argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            code = ae_comp.main(argv)
        return code, err.getvalue()

    def job(self, argv):
        return ae_comp.build_job(ae_comp.parse_args(argv))

    def test_writes_ascii_jsx_with_layers_bottom_to_top(self):
        shot_dir, argv = self.shot()
        self.assertEqual(self.generate(argv)[0], 0)
        jsx = shot_dir / "ae" / "build_comp.jsx"
        text = jsx.read_bytes().decode("ascii")
        self.assertNotIn(ae_comp.PLACEHOLDER, text)
        job = job_from_jsx(text)
        self.assertEqual([layer["name"] for layer in job["layers"]], [spec["name"] for spec in ae_comp.LAYERS])
        self.assertEqual([layer["frames"] for layer in job["layers"]], [10] + [6] * len(RESULTS))
        self.assertEqual(job["fps_ratio"], [30000, 1001])
        self.assertEqual(job["project"], ae_comp.PROJECT)
        self.assertEqual(Path(job["receipt"]), shot_dir / "ae" / "build_comp.result.json")
        self.assertTrue(job["layers"][0]["path"].endswith("frame_0001.png"))
        self.assertFalse(job["dialogs"])

    def test_result_start_frame_must_fit_the_plate(self):
        _, argv = self.shot(plate_frames=10, result_frames=6)
        role = RESULTS[-1]["role"]
        job = self.job(argv + [f"--{role}-start", "4"])
        self.assertEqual(job["layers"][-1]["start_frame"], 4)
        with self.assertRaisesRegex(ae_comp.CompError, "does not fit"):
            self.job(argv + [f"--{role}-start", "5"])
        with self.assertRaisesRegex(ae_comp.CompError, "does not fit"):
            self.job(argv + [f"--{role}-start", "-1"])

    def test_fps_comes_from_the_contract_when_omitted(self):
        shot_dir, argv = self.shot()
        argv = argv[:argv.index("--fps")] + argv[argv.index("--fps") + 2:]
        with self.assertRaisesRegex(ae_comp.CompError, "--fps"):
            self.job(argv)
        (shot_dir / ae_comp.CONTRACT).write_text('{"fps": [24000, 1001]}', encoding="utf-8")
        self.assertEqual(self.job(argv)["fps_ratio"], [24000, 1001])

    def test_ratio_forms(self):
        self.assertEqual(ae_comp.parse_ratio("30000/1001", "fps"), ae_comp.Fraction(30000, 1001))
        self.assertEqual(ae_comp.parse_ratio([25, 1], "fps"), 25)
        self.assertEqual(ae_comp.parse_ratio("29.97", "fps"), ae_comp.Fraction(2997, 100))
        for bad in ("abc", 0, "-24", True, [1, 0], None):
            with self.assertRaises(ae_comp.CompError):
                ae_comp.parse_ratio(bad, "fps")

    def test_sequence_gaps_mixed_names_and_movies_are_rejected(self):
        shot_dir, argv = self.shot()
        plate = shot_dir / PLATE["default"]
        (plate / "frame_0005.png").unlink()
        with self.assertRaisesRegex(ae_comp.CompError, "missing frame numbers \\[5\\]"):
            self.job(argv)
        (plate / "frame_0005.png").write_bytes(b"")
        (plate / "frame_00011.png").write_bytes(b"")  # different padding sorts out of order in AE
        with self.assertRaisesRegex(ae_comp.CompError, "one sequence per folder"):
            self.job(argv)
        (plate / "frame_00011.png").unlink()
        (plate / "notes.txt").write_bytes(b"")
        with self.assertRaisesRegex(ae_comp.CompError, "not a numbered image"):
            self.job(argv)
        (plate / "notes.txt").unlink()
        (plate / ".DS_Store").write_bytes(b"")
        self.assertEqual(self.job(argv)["layers"][0]["frames"], 10)
        role = RESULTS[-1]["role"]
        movie = shot_dir / "source" / "clip.mov"
        movie.parent.mkdir()
        movie.write_bytes(b"")
        with self.assertRaisesRegex(ae_comp.CompError, "FFmpeg"):
            self.job(argv + [f"--{role}", str(movie)])

    def test_stills_only_where_the_preset_allows_them(self):
        shot_dir, argv = self.shot()
        image = shot_dir / "still.png"
        image.write_bytes(b"")
        for spec in RESULTS:
            if spec.get("still"):
                job = self.job(argv + [f"--{spec['role']}", str(image)])
                layer = next(layer for layer in job["layers"] if layer["name"] == spec["name"])
                self.assertEqual((layer["kind"], layer["frames"]), ("still", None))
            else:
                with self.assertRaises(ae_comp.CompError):
                    self.job(argv + [f"--{spec['role']}", str(image)])

    @unittest.skipUnless(ae_comp.PIXEL_ASPECT_OPTION, "no pixel aspect option in this repository")
    def test_pixel_aspect_applies_to_plate_and_results_only(self):
        shot_dir, argv = self.shot()
        job = self.job(argv + ["--pixel-aspect", "3/2"])
        expected = {spec["name"]: 1.5 if spec.get("from_plate", True) else None for spec in ae_comp.LAYERS}
        self.assertEqual({layer["name"]: layer["pixel_aspect"] for layer in job["layers"]}, expected)
        (shot_dir / ae_comp.CONTRACT).write_text('{"pixel_aspect": [3, 2]}', encoding="utf-8")
        self.assertEqual(self.job(argv)["layers"][0]["pixel_aspect"], 1.5)

    def test_non_ascii_shot_and_path_are_escaped(self):
        shot = "키잉_테스트"
        shot_dir, argv = self.shot(shot=shot)
        self.assertEqual(self.generate(argv)[0], 0)
        text = (shot_dir / "ae" / "build_comp.jsx").read_bytes().decode("ascii")
        job = job_from_jsx(text)
        self.assertEqual(job["shot"], shot)
        self.assertIn(shot, job["layers"][0]["path"])

    def test_bad_shot_names_and_missing_paths(self):
        _, argv = self.shot()
        for name in ("a b", "../x", ".hidden", ""):
            bad = list(argv)
            bad[bad.index("--shot") + 1] = name
            with self.assertRaisesRegex(ae_comp.CompError, "shot name"):
                self.job(bad)
        role = RESULTS[-1]["role"]
        code, err = self.generate(argv + [f"--{role}", str(self.work / "nowhere")])
        self.assertEqual(code, 2)
        self.assertIn("path not found", err)

    def test_template(self):
        text = ae_comp.TEMPLATE.read_bytes().decode("ascii")
        self.assertEqual(text.count(ae_comp.PLACEHOLDER), 1)
        # Writing "None" to workingSpace makes AE show a warning dialog; "" clears it.
        self.assertNotRegex(text, r'workingSpace\s*=\s*"None"')
        for word in ("project.save", "project.close", "renderQueue", "app.quit"):
            self.assertNotIn(word, text)
        used = set(re.findall(r"job\.messages\.(\w+)", text))
        self.assertTrue(used)
        self.assertLessEqual(used, set(ae_comp.MESSAGES))

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_generated_jsx_parses(self):
        shot_dir, argv = self.shot()
        self.assertEqual(self.generate(argv)[0], 0)
        script = shot_dir / "ae" / "check.js"
        shutil.copyfile(shot_dir / "ae" / "build_comp.jsx", script)
        result = subprocess.run([shutil.which("node"), "--check", str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
