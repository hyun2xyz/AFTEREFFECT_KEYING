#!/usr/bin/env python3
"""Pull a Keylight key in After Effects in recorded rounds and measure every round.

  python -B scripts/keylight.py plan    --shot <shot>   screen colour + garbage polygon -> shot.json
  python -B scripts/ae_comp.py  keylight --shot <shot> --fps <fps>        builds the comp (once)
  python -B scripts/keylight.py round   --shot <shot> [--set edge.clip_black=20 ...] [--core on|off]
  python -B scripts/keylight.py run     <script.jsx> [--app "Adobe After Effects 2026"]
  python -B scripts/keylight.py analyze --shot <shot> [--round N]

plan and analyze read the plate and write PNG sheets, so they need NumPy and OpenCV (the .venv from
scripts/setup_environment.py --install). round and run use the standard library only. Every round keeps its script, its
receipt, the rendered check frames and report.json under work/<shot>/keylight/round_NN/.

The measurements come from the source plate, never from Keylight: pixels whose colour is clearly the
screen must end at alpha 0, pixels clearly not the screen (eroded away from every edge) at alpha 1, and
everything outside the garbage polygon at 0. The edge band in between is reported, not gated; look at it.
Spill is reported the same way: the share of the soft edge and of the solid subject whose keyed colour still
leans to the screen (a subject that is really green counts too).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ae_comp import (EXTRA_EFFECTS, KEYLIGHT, KEYLIGHT_PARAMS, ROOT, VIEW, CompError,  # noqa: E402
                     describe_sequence, keylight_params, parse_colour)

TEMPLATE = HERE / "keylight_round.jsx"
PLACEHOLDER = "/*__ROUND_JOB__*/"
EFFECTS = {"core": "Keylight Core", "edge": "Keylight Edge", "cleaner": "Key Cleaner", "spill": "Spill"}
# Normalised screen excess: (screen channel - larger other channel) / screen channel.
SCREEN = 0.25    # at or above: clearly the screen (shadows on the screen included)
SUBJECT = 0.08   # below: clearly not the screen
DARK = 0.25      # a screen channel under this share of the screen colour's is subject, whatever its tint
# Largest allowed fraction per frame. garbage_seam is the band just inside the garbage polygon, where a
# shadowed seam next to a flag keys worse than open screen.
GATE = {"bg_leak": 0.0005, "garbage_leak": 0.0005, "garbage_seam": 0.0005, "core_holes": 0.0005}
LOW, HIGH = 2 / 255, 253 / 255
SPILL = 0.02     # soft-edge share above this gets the spill hint


def fail(message):
    raise CompError(message)


def shot_paths(work, shot):
    shot_dir = Path(work).expanduser().resolve() / shot
    return shot_dir, shot_dir / "shot.json", shot_dir / "keylight"


def read_json(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"{what} not found: {path}")
    except ValueError as error:
        fail(f"cannot read {path}: {error}")


def plate_files(shot_dir):
    first, count = describe_sequence(shot_dir / "frames")
    return sorted(p for p in first.parent.iterdir() if p.suffix == first.suffix and not p.name.startswith("."))[:count]


def sample_frames(count, n=5):
    if count <= n:
        return list(range(count))
    return sorted({round(i * (count - 1) / (n - 1)) for i in range(n)})


# ---- image helpers (NumPy/OpenCV, imported only where needed) -------------------------------------

def imaging():
    try:
        import cv2
        import numpy as np
    except ImportError:
        fail("plan and analyze need NumPy and OpenCV; run them with the .venv Python "
             "(scripts/setup_environment.py --install)")
    return np, cv2


def load_rgb(path):
    """PNG/TIFF/JPEG -> float RGB 0..1 (8- or 16-bit)."""
    np, cv2 = imaging()
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        fail(f"cannot read image: {path}")
    scale = 65535.0 if image.dtype == np.uint16 else 255.0
    if image.ndim == 2:
        image = np.repeat(image[..., None], 3, axis=2)
    return image[..., 2::-1][..., :3].astype(np.float32) / scale


def load_rgba8(path):
    np, cv2 = imaging()
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None or image.ndim != 3 or image.shape[2] != 4:
        fail(f"expected an RGBA PNG from AE: {path}")
    scale = 65535.0 if image.dtype == np.uint16 else 255.0
    image = image.astype(np.float32) / scale
    return image[..., [2, 1, 0]], image[..., 3]


def screen_excess(rgb, screen):
    np, _ = imaging()
    key = rgb[..., 1] if screen == "green" else rgb[..., 2]
    other = np.maximum(rgb[..., 0], rgb[..., 2] if screen == "green" else rgb[..., 1])
    return (key - other) / np.maximum(key, 1e-4)


def classify(rgb, screen, colour):
    """(screen, subject) masks from the source plate alone. Near black the excess ratio is noise
    (dark clothes read as pure green), so pixels much darker than the screen count as subject."""
    excess = screen_excess(rgb, screen)
    channel = 1 if screen == "green" else 2
    bright = rgb[..., channel] >= DARK * colour[channel]
    return (excess > SCREEN) & bright, (excess < SUBJECT) | ~bright


def disk(radius):
    _, cv2 = imaging()
    size = 2 * int(radius) + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def erode(mask, radius):
    np, cv2 = imaging()
    return cv2.erode(mask.astype(np.uint8), disk(radius)) > 0 if radius > 0 else mask


def dilate(mask, radius):
    np, cv2 = imaging()
    return cv2.dilate(mask.astype(np.uint8), disk(radius)) > 0 if radius > 0 else mask


def keep_mask(shape, polygon):
    np, cv2 = imaging()
    keep = np.zeros(shape, np.uint8)
    if polygon:
        cv2.fillPoly(keep, [np.round(np.array(polygon)).astype(np.int32)], 1)
    else:
        keep[:] = 1
    return keep > 0


def to8(rgb):
    np, _ = imaging()
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


def save_rgb(path, rgb):
    _, cv2 = imaging()
    cv2.imwrite(str(path), to8(rgb)[..., ::-1])


# ---- plan --------------------------------------------------------------------------------------------

def plan(args):
    np, cv2 = imaging()
    shot_dir, shot_json, key_dir = shot_paths(args.work, args.shot)
    files = plate_files(shot_dir)
    frames = [int(f) for f in args.frames.split(",")] if args.frames else sample_frames(len(files))
    images = [load_rgb(files[f]) for f in frames]
    h, w = images[0].shape[:2]
    green = sum(float(np.mean(screen_excess(im, "green") > SCREEN)) for im in images)
    blue = sum(float(np.mean(screen_excess(im, "blue") > SCREEN)) for im in images)
    screen = "green" if green >= blue else "blue"

    samples = []
    for image in images:
        pixels = image[screen_excess(image, screen) > SCREEN]
        luma = pixels @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        lo, hi = np.percentile(luma, [25, 90])
        samples.append(pixels[(luma >= lo) & (luma <= hi)])
    colour = [round(float(v), 4) for v in np.median(np.concatenate(samples), axis=0)]

    # Garbage: non-screen areas joined to the frame border in every sampled frame (flags, stands,
    # letterbox). The subject moves, so it is not garbage in all of them; one that never leaves a border
    # is named with --subject-touches. The keep region is the rest, pulled in by a margin of about 1/72 of
    # the height, so the polygon crosses screen that keys cleanly rather than the shadowed seam by a flag.
    margin = args.margin if args.margin is not None else max(4, round(h / 72))
    open_borders = {"top", "bottom", "left", "right"} - set((args.subject_touches or "").split(","))
    garbage = np.ones((h, w), bool)
    for image in images:
        non_screen = ~classify(image, screen, colour)[0]
        non_screen = cv2.morphologyEx(non_screen.astype(np.uint8), cv2.MORPH_OPEN, disk(1)) > 0
        count, labels = cv2.connectedComponents(non_screen.astype(np.uint8))
        edges = {"top": labels[0], "bottom": labels[-1], "left": labels[:, 0], "right": labels[:, -1]}
        border = set()
        for side in open_borders:
            border |= set(np.unique(edges[side]).tolist())
        border.discard(0)
        garbage &= np.isin(labels, list(border))
    region = ~dilate(garbage, margin)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(region.astype(np.uint8))
    region = labels == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    contours, _ = cv2.findContours(region.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = max(contours, key=cv2.contourArea)
    # Simplify by less than the margin so the polygon never reaches into the garbage; +0.5 puts the
    # points on pixel centres in AE's layer space.
    approx = cv2.approxPolyDP(contour, max(1.0, 0.8 * margin), True)
    polygon = [[int(x) + 0.5, int(y) + 0.5] for x, y in approx[:, 0]]
    covers_frame = region.mean() > 0.995

    # The polygon cuts the subject where non-screen pixels just outside it join non-screen pixels inside.
    keep = keep_mask((h, w), polygon)
    outside = dilate(keep, margin) & ~keep
    edge_hits = np.zeros((h, w), bool)
    for image in images:
        subject = classify(image, screen, colour)[1]
        edge_hits |= outside & subject & dilate(subject & keep, 2)
    touching = int(np.count_nonzero(edge_hits))

    contract = read_json(shot_json, "shot.json") if shot_json.exists() else {}
    contract["keylight"] = {"screen": screen, "screen_colour": colour,
                            "garbage": None if covers_frame else polygon,
                            "planned_from_frames": frames, "planned_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    shot_json.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    key_dir.mkdir(parents=True, exist_ok=True)
    preview = np.ascontiguousarray(to8(images[len(images) // 2])[..., ::-1])
    if not covers_frame:
        cv2.polylines(preview, [np.array(polygon, np.int32)], True, (0, 0, 255), max(1, h // 360))
        preview[dilate(edge_hits, 1)] = (255, 0, 255)
    swatch = (np.array(colour[::-1]) * 255).astype(np.uint8)
    preview[: h // 8, : h // 8] = swatch
    cv2.imwrite(str(key_dir / "plan.png"), preview)
    print(f"screen: {screen}  colour (0-1 RGB): {colour}  frames {frames}")
    print("garbage: " + ("none (screen fills the frame)" if covers_frame else f"{len(polygon)}-point polygon, {margin}px inside the screen"))
    if touching:
        print(f"WARNING: the garbage polygon cuts {touching} non-screen pixels (magenta on plan.png). If that is "
              "the subject, run plan with a smaller --margin or --subject-touches <edge>, or edit keylight.garbage")
    print(f"written: {shot_json} (keylight)  preview: {key_dir / 'plan.png'}")
    return 0


# ---- round -------------------------------------------------------------------------------------------

def parse_set(items):
    """['edge.clip_black=20', 'spill.enabled=on'] -> {effect: {'params': {...}, 'enabled': ...}}"""
    changes = {}
    for item in items or []:
        match = re.fullmatch(r"(\w+)\.(\w+)=(.+)", item.strip())
        if not match or match.group(1) not in EFFECTS:
            fail(f"--set takes effect.parameter=value with effect one of {', '.join(EFFECTS)}: {item!r}")
        alias, name, value = match.groups()
        change = changes.setdefault(EFFECTS[alias], {"params": {}, "enabled": None})
        if name == "enabled":
            if value not in ("on", "off"):
                fail(f"{alias}.enabled takes on or off")
            change["enabled"] = value == "on"
        elif alias in ("core", "edge"):
            if name.endswith("colour") or name.endswith("bias"):
                change["params"].update(keylight_params({name: parse_colour(value)}))
            else:
                change["params"].update(keylight_params({name: float(value)}))
        else:
            match_names = EXTRA_EFFECTS[EFFECTS[alias]][1]
            if name not in match_names:
                fail(f"{alias} parameters: {', '.join(match_names)}, enabled")
            number = parse_colour(value) + [1.0] if name.endswith("color") else float(value)
            change["params"][match_names[name]] = number
    return changes


def round_job(args):
    shot_dir, shot_json, key_dir = shot_paths(args.work, args.shot)
    build = read_json(shot_dir / "ae" / "build_comp.result.json", "build receipt (run ae_comp.py keylight in AE first)")
    if build.get("status") != "ok" or not build.get("keylight"):
        fail("the last build_comp.result.json is not a successful keylight build")
    names = [layer["name"] for layer in build["layers"]]
    changes = parse_set(args.set)
    if args.core:
        on = args.core == "on"
        changes.setdefault(EFFECTS["core"], {"params": {}, "enabled": None})["enabled"] = on
        changes.setdefault(EFFECTS["edge"], {"params": {}, "enabled": None})["params"].update(
            keylight_params({"source_alpha": 2 if on else 1}))
    garbage = None
    if args.garbage:
        garbage = (read_json(shot_json, "shot.json").get("keylight") or {}).get("garbage")
        if not garbage:
            fail("shot.json has no keylight.garbage polygon to send")
    rounds = sorted(key_dir.glob("round_[0-9][0-9]"))
    number = int(rounds[-1].name[6:]) + 1 if rounds else 1
    out_dir = key_dir / f"round_{number:02d}"
    out_dir.mkdir(parents=True)
    total = build["comp"]["frames"]
    if args.frames:
        frames = [int(f) for f in args.frames.split(",")]
    else:
        planned = (read_json(shot_json, "shot.json").get("keylight") or {}).get("planned_from_frames")
        frames = planned or sample_frames(total)
    if any(f < 0 or f >= total for f in frames):
        fail(f"frames must be within 0..{total - 1}: {frames}")
    has_background = "Background" in names
    views = [{"name": "status", "edge_view": VIEW["status"], "background": False},
             {"name": "final", "edge_view": VIEW["final"], "background": False},
             {"name": "core", "core_view": VIEW["combined_matte"], "background": False}]
    if has_background:
        views.insert(2, {"name": "comp", "edge_view": VIEW["final"], "background": True})
    read = [{"name": EFFECTS[a], "params": {n: f"{KEYLIGHT}-{KEYLIGHT_PARAMS[n]}" for n in KEYLIGHT_PARAMS}}
            for a in ("core", "edge")]
    read += [{"name": name, "params": params} for name, (_, params) in EXTRA_EFFECTS.items()]
    job = {
        "job_id": uuid.uuid4().hex[:12], "round": number, "shot": args.shot,
        "comp_name": build["comp"]["name"], "layer": "Plate", "background": "Background" if has_background else None,
        "changes": [{"effect": e, "params": c["params"], "enabled": c["enabled"]} for e, c in changes.items()],
        "garbage": garbage, "read": read, "frames": frames, "fps": build["comp"]["fps"], "views": views,
        "match": {"view": f"{KEYLIGHT}-{KEYLIGHT_PARAMS['view']}"},
        "edge_view_normal": VIEW["final"], "core_view_normal": VIEW["intermediate"],
        "out_dir": str(out_dir), "receipt": str(out_dir / "round.result.json"), "wait_ms": 120000,
        "request": {"set": args.set or [], "core": args.core, "garbage": bool(args.garbage)},
    }
    return job, out_dir


def write_round(job, out_dir):
    template = TEMPLATE.read_text(encoding="ascii")
    if template.count(PLACEHOLDER) != 1:
        fail(f"{TEMPLATE} must contain {PLACEHOLDER} once")
    jsx = out_dir / "round.jsx"
    jsx.write_text(template.replace(PLACEHOLDER, json.dumps(job, ensure_ascii=True)), encoding="ascii", newline="\n")
    (out_dir / "request.json").write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return jsx


def round_cmd(args):
    job, out_dir = round_job(args)
    jsx = write_round(job, out_dir)
    print(f"round {job['round']:02d}: {jsx}")
    for change in job["changes"]:
        state = "" if change["enabled"] is None else (" on" if change["enabled"] else " off")
        print(f"  {change['effect']}{state} {change['params'] or ''}")
    print(f"  check frames {job['frames']}: {', '.join(v['name'] for v in job['views'])}")
    print(f"next: keylight.py run {jsx}  then  keylight.py analyze --shot {job['shot']}")
    return 0


# ---- run ---------------------------------------------------------------------------------------------

def running_ae():
    """Name of the running After Effects on macOS, such as 'Adobe After Effects 2026'."""
    listing = subprocess.run(["ps", "-axo", "comm"], capture_output=True, text=True).stdout
    names = sorted(set(re.findall(r"/(Adobe After Effects \d{4})\.app/Contents/MacOS/After Effects", listing)))
    if len(names) != 1:
        fail(f"start one After Effects first, or pass --app (found: {names or 'none'})")
    return names[0]


def run(args):
    jsx = Path(args.jsx).expanduser().resolve()
    text = jsx.read_text(encoding="ascii")
    found = re.search(r'"job_id": "([0-9a-f]{12})"', text)
    if not found:
        fail(f"{jsx} is not a script written by ae_comp.py or keylight.py")
    job_id = found.group(1)
    receipt = jsx.with_name("build_comp.result.json" if jsx.name == "build_comp.jsx" else f"{jsx.stem}.result.json")
    if receipt.exists():
        receipt.unlink()  # a receipt from an earlier run must not be read as this one
    if sys.platform == "darwin":
        app = args.app or running_ae()
        command = ["osascript", "-e", f'tell application "{app}" to DoScriptFile "{jsx}"']
    elif os.name == "nt":
        if not args.afterfx:
            fail("pass --afterfx with the path of AfterFX.exe (Support Files folder)")
        command = [args.afterfx, "-r", str(jsx)]
    else:
        fail("After Effects runs on macOS and Windows only")
    started = subprocess.run(command, capture_output=True, text=True)
    if started.returncode != 0:
        fail(f"could not hand the script to After Effects: {started.stderr.strip() or started.returncode}")
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if receipt.exists():
            try:
                result = json.loads(receipt.read_text(encoding="utf-8"))
            except ValueError:
                time.sleep(0.5)  # still being written
                continue
            if result.get("job_id") != job_id:
                fail(f"{receipt} belongs to another job ({result.get('job_id')}), expected {job_id}")
            print(f"{result.get('status')}: {receipt}")
            if result.get("error"):
                print(f"error: {result['error']}")
            return 0 if result.get("status") == "ok" else 1
        time.sleep(0.5)
    fail(f"no receipt after {args.timeout}s: {receipt}. Look at After Effects for an open dialog before resending.")


# ---- analyze -----------------------------------------------------------------------------------------

def frame_metrics(plate, alpha, keep, screen, colour, keyed=None):
    np, _ = imaging()
    h = plate.shape[0]
    is_screen, is_subject = classify(plate, screen, colour)
    subject = is_subject & keep
    # A dark edge mixed with the screen keeps a high normalised excess, so the screen test stays
    # as far from the subject as the inside test stays from the screen; the band between is looked at.
    away = max(4, round(h / 120))
    screen_px = erode(is_screen & keep, max(2, round(h / 360))) & ~dilate(subject, away)
    core = erode(subject, away)
    garbage = erode(~keep, 2)
    near = max(2, round(h / 240))
    seam = keep & ~erode(keep, 2 * near) & ~dilate(core, 2 * away)
    band = dilate(subject, near) & dilate(is_screen, near) & keep

    def share(mask, test):
        n = int(np.count_nonzero(mask))
        return (float(np.count_nonzero(mask & test)) / n if n else 0.0), n
    bg_leak, n_screen = share(screen_px, alpha > LOW)
    garbage_leak, n_garbage = share(garbage, alpha > LOW)
    garbage_seam, n_seam = share(seam, alpha > LOW)
    core_holes, n_core = share(core, alpha < HIGH)
    edge_partial, n_band = share(band, (alpha > LOW) & (alpha < HIGH))
    spill_edge = spill_solid = None
    if keyed is not None:
        # Keyed colour still leaning to the screen; the floor skips near-black pixels where the ratio is noise.
        channel = 1 if screen == "green" else 2
        tinted = (screen_excess(keyed, screen) > SUBJECT) & (keyed[..., channel] >= 8 / 255)
        spill_edge = round(share((alpha > 0.05) & (alpha < 0.95), tinted)[0], 4)
        spill_solid = round(share(alpha >= 0.95, tinted)[0], 4)
    return {
        "bg_leak": round(bg_leak, 6), "bg_max": round(float(alpha[screen_px].max()) if n_screen else 0.0, 4),
        "garbage_leak": round(garbage_leak, 6), "garbage_seam": round(garbage_seam, 6),
        "core_holes": round(core_holes, 6), "core_min": round(float(alpha[core].min()) if n_core else 1.0, 4),
        "edge_partial": round(edge_partial, 4), "spill_edge": spill_edge, "spill_solid": spill_solid,
        "pixels": {"screen": n_screen, "garbage": n_garbage, "seam": n_seam, "core": n_core, "edge_band": n_band},
        "_masks": {"leak": (screen_px | garbage | seam) & (alpha > LOW), "holes": core & (alpha < HIGH)},
    }


def checker(h, w, size=16):
    np, _ = imaging()
    y, x = np.mgrid[0:h, 0:w]
    tile = (((y // size) + (x // size)) % 2).astype(np.float32)
    return np.repeat((0.35 + 0.3 * tile)[..., None], 3, axis=2)


def sheet(rows, path, height=270):
    np, cv2 = imaging()
    out = []
    for row in rows:
        scaled = [cv2.resize(to8(p), (round(height * p.shape[1] / p.shape[0]), height), interpolation=cv2.INTER_AREA)
                  for p in row]
        out.append(np.concatenate([np.pad(s, ((0, 0), (0, 4), (0, 0))) for s in scaled], axis=1))
    widest = max(r.shape[1] for r in out)
    out = [np.pad(r, ((0, 4), (0, widest - r.shape[1]), (0, 0))) for r in out]
    cv2.imwrite(str(path), np.concatenate(out, axis=0)[..., ::-1])


def zoom(image, centre, size, factor=2):
    np, cv2 = imaging()
    h, w = image.shape[:2]
    half = size // 2
    y = min(max(centre[0], half), h - half)
    x = min(max(centre[1], half), w - half)
    crop = image[y - half:y + half, x - half:x + half]
    return cv2.resize(crop, (crop.shape[1] * factor, crop.shape[0] * factor), interpolation=cv2.INTER_NEAREST)


def analyze(args):
    np, _ = imaging()
    shot_dir, shot_json, key_dir = shot_paths(args.work, args.shot)
    rounds = sorted(key_dir.glob("round_[0-9][0-9]"))
    if not rounds:
        fail("no rounds yet; run keylight.py round first")
    out_dir = key_dir / f"round_{args.round:02d}" if args.round else rounds[-1]
    job = read_json(out_dir / "request.json", "round request")
    receipt = read_json(out_dir / "round.result.json", "round receipt (run the round's script in AE)")
    if receipt.get("job_id") != job["job_id"] or receipt.get("status") != "ok":
        fail(f"round receipt is not a successful run of this round: {receipt.get('error') or receipt.get('job_id')}")
    settings = read_json(shot_json, "shot.json").get("keylight") or {}
    screen = settings.get("screen", "green")
    colour = settings.get("screen_colour") or fail("shot.json has no keylight.screen_colour; run plan first")
    files = plate_files(shot_dir)
    first = files[0]
    h, w = load_rgb(first).shape[:2]
    keep = keep_mask((h, w), settings.get("garbage"))

    report = {"round": job["round"], "job_id": job["job_id"], "gate": GATE, "frames": [], "effects": receipt["effects"]}
    rows, failures = [], []
    for frame in job["frames"]:
        plate = load_rgb(files[frame])
        final_rgb, alpha = load_rgba8(out_dir / f"final_{frame:04d}.png")
        metrics = frame_metrics(plate, alpha, keep, screen, colour, final_rgb)
        masks = metrics.pop("_masks")
        verdict = all(metrics[k] <= GATE[k] for k in GATE)
        report["frames"].append({"frame": frame, "pass": verdict, **metrics})
        status_rgb, _ = load_rgba8(out_dir / f"status_{frame:04d}.png")
        over = final_rgb * alpha[..., None] + checker(h, w) * (1 - alpha[..., None])
        row = [plate, status_rgb, over]
        if (out_dir / f"comp_{frame:04d}.png").exists():
            row.append(load_rgba8(out_dir / f"comp_{frame:04d}.png")[0])
        if (out_dir / f"core_{frame:04d}.png").exists():
            row.append(load_rgba8(out_dir / f"core_{frame:04d}.png")[0])
        problem = masks["leak"] | masks["holes"]
        if np.any(problem):
            ys, xs = np.nonzero(problem)
            centre = (int(np.median(ys)), int(np.median(xs)))
            failures.append(frame)
        else:
            ys, xs = np.nonzero(classify(plate, screen, colour)[1] & keep)
            top = int(np.argmin(ys)) if len(ys) else 0
            centre = (int(ys[top]) if len(ys) else h // 2, int(xs[top]) if len(xs) else w // 2)
        size = max(64, h // 5)
        row.append(zoom(over, centre, size))
        rows.append(row)
    sheet(rows, out_dir / "sheet.png")

    report["pass"] = all(f["pass"] for f in report["frames"])
    worst = lambda key: max(report["frames"], key=lambda f: f[key])  # noqa: E731
    hints = []
    if worst("bg_leak")["bg_leak"] > GATE["bg_leak"]:
        hints.append("Screen shows through as grey: raise edge.clip_black in steps of 5 while Status stays black; "
                     "leaks along rigs or the frame border belong to the garbage polygon, not Clip Black.")
    if worst("garbage_leak")["garbage_leak"] > GATE["garbage_leak"]:
        hints.append("Pixels outside the garbage polygon survive: check that the Plate's track matte is the "
                     "Garbage Matte layer (round --garbage resends the polygon).")
    # With a veil over the whole screen the seam fails too; it only means a seam once the open screen is clean.
    if worst("garbage_seam")["garbage_seam"] > GATE["garbage_seam"] and worst("bg_leak")["bg_leak"] <= GATE["bg_leak"]:
        hints.append("A thin line survives just inside the garbage polygon (a shadowed seam by a flag): run plan "
                     "again with a larger --margin, then round --garbage.")
    if worst("core_holes")["core_holes"] > GATE["core_holes"]:
        hints.append("The subject is see-through: lower edge.clip_white in steps of 5 (not much below 70); "
                     "dark or spill-lit areas that stay grey call for the core pass (--core on).")
    if worst("spill_edge")["spill_edge"] > SPILL:
        hue = "0,1,0" if screen == "green" else "0,0,1"
        hints.append(f"Edges keep a {screen} cast ({worst('spill_edge')['spill_edge']:.0%} of the soft edge): "
                     f"spill.enabled=on with spill.method=2 and spill.key_color={hue} (the pure hue, not the "
                     "measured screen colour). If the subject itself is that colour, judge on the sheet instead.")
    if len(rounds) > 1 and rounds[0] != out_dir:
        base = read_json(rounds[0] / "report.json", "first round report") if (rounds[0] / "report.json").exists() else None
        if base:
            before = sum(f["edge_partial"] for f in base["frames"]) / len(base["frames"])
            now = sum(f["edge_partial"] for f in report["frames"]) / len(report["frames"])
            report["edge_partial_vs_round_1"] = round(now / before, 3) if before else None
            if before and now < 0.6 * before:
                hints.append(f"Edges hardened ({now:.2f} soft edge share vs {before:.2f} in round 1): add "
                             "edge.clip_rollback 1-3 or edge.softness 0.5-1, or let the core pass hold the inside.")
    report["hints"] = hints
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"round {job['round']:02d}: {'PASS' if report['pass'] else 'FAIL'} (gate per frame: {GATE})")
    for f in report["frames"]:
        print(f"  frame {f['frame']:>4}: bg_leak {f['bg_leak']:.4%} (max {f['bg_max']:.3f})  "
              f"garbage {f['garbage_leak']:.4%}  seam {f['garbage_seam']:.4%}  holes {f['core_holes']:.4%} (min {f['core_min']:.3f})  "
              f"soft edge {f['edge_partial']:.2f}  spill {f['spill_edge']:.0%}/{f['spill_solid']:.0%}  "
              f"{'ok' if f['pass'] else 'FAIL'}")
    for hint in hints:
        print(f"  hint: {hint}")
    print(f"look: {out_dir / 'sheet.png'} (plate | Status | key over checker | ... | zoom); "
          "spill is soft edge/solid share still tinted")
    print("Numbers check the screen and the solid inside; hair, motion blur and spill need your eyes on the sheet "
          "and in AE.")
    return 0


# ---- command line ------------------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "round", "analyze"):
        item = sub.add_parser(name)
        item.add_argument("--shot", required=True)
        item.add_argument("--work", default=str(ROOT / "work"))
        if name in ("plan", "round"):
            item.add_argument("--frames", help="comma-separated comp frames (default: five spread over the plate)")
        if name == "plan":
            item.add_argument("--margin", type=int, help="pixels the garbage polygon stays inside the screen "
                                                          "(default: height/72, at least 4)")
            item.add_argument("--subject-touches", help="frame edges the subject itself crosses, such as bottom "
                                                         "(those edges do not start garbage)")
    rnd = sub.choices["round"]
    rnd.add_argument("--set", action="append", metavar="EFFECT.PARAM=VALUE",
                     help=f"effect: {', '.join(EFFECTS)}; Keylight parameters: {', '.join(KEYLIGHT_PARAMS)}; "
                          "any effect also takes enabled=on|off")
    rnd.add_argument("--core", choices=["on", "off"], help="switch the core pass (and the edge pass's Source Alpha)")
    rnd.add_argument("--garbage", action="store_true", help="resend keylight.garbage from shot.json to the garbage matte")
    sub.choices["analyze"].add_argument("--round", type=int, help="round number (default: latest)")
    runner = sub.add_parser("run")
    runner.add_argument("jsx")
    runner.add_argument("--app", help="macOS app name (default: the running After Effects)")
    runner.add_argument("--afterfx", help="Windows: path of AfterFX.exe")
    runner.add_argument("--timeout", type=float, default=300)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        return {"plan": plan, "round": round_cmd, "run": run, "analyze": analyze}[args.command](args)
    except (CompError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
