#!/usr/bin/env python3
"""Write the After Effects JSX that builds one shot's comp from the plate and result layers.

  python -B scripts/ae_comp.py keying   --shot <shot> --key <folder> [--background <file>]
  python -B scripts/ae_comp.py keylight --shot <shot> [--screen-colour R,G,B] [--background <file>]

Without a preset name the keying preset is used (python -B scripts/ae_comp.py --shot <shot> --key ...).
The JSX goes to work/<shot>/ae/build_comp.jsx. The student opens a new, empty project and runs it with
File > Scripts > Run Script File (or scripts/keylight.py run sends it to the running AE); it writes
build_comp.result.json next to itself and shows no message unless that file cannot be written. A sequence is a folder of contiguously numbered, zero-padded frames.
Standard library only.
"""

import argparse
import json
import re
import sys
import uuid
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().with_name("ae_comp.jsx")
PLACEHOLDER = "/*__COMP_JOB__*/"
IMAGE_SUFFIXES = {".png", ".exr", ".tif", ".tiff", ".jpg", ".jpeg", ".dpx", ".tga"}
NUMBERED = re.compile(r"^(.*?)(\d+)(\.[^.]+)$")

# Presets from docs/rules.md section 7.
# layers run bottom to top; the plate layer sets the comp size and length.
# default: folder under work/<shot>/ used when the option is omitted.
# from_plate (default true): rendered from the plate, so same size and within its frames.
# A key delivered as EXR (CorridorKey --output_format exr) is scene-linear sRGB: CorridorKey decodes with the
# IEC 61966-2-1 curve and blends fg*a + bg*(1-a) in linear light, so the comp matches it with 32 bpc, an sRGB
# working space and linear blending. AE then reads the float EXR as linear light (its default for 32 bpc).
# Checked in AE 26.5 (macOS) with a float cutout sequence in CorridorKey's layout: the comp shows the
# sRGB-encoded EXR within 0.0015, values above 1.0 survive and the straight alpha matches exactly.
LINEAR_SRGB_32 = {"bits_per_channel": 32, "working_space": "sRGB IEC61966-2.1", "linear_blending": True}
PRESETS = {
    "keying": {
        "help": "disabled reference plate + background + straight key; colour settings left as they are",
        "contract": "shot.json", "comp_suffix": "key", "pixel_aspect": True,
        "project": {"bits_per_channel": 16, "working_space": None, "linear_blending": None},
        "layers": [
            {"role": "plate", "name": "Plate (reference)", "default": "frames", "alpha": "ignore", "enabled": False},
            {"role": "background", "name": "Background", "alpha": "ignore", "still": True, "from_plate": False,
             "help": "background image file or sequence folder"},
            {"role": "key", "name": "Key", "alpha": "straight", "required": True,
             "help": "keyed straight RGBA sequence, such as the CorridorKey cutout"},
        ],
    },
    "keylight": {
        "help": "background + plate keyed in AE with Keylight 1.2 (edge pass, core pass off, garbage matte, spill)",
        "contract": "shot.json", "comp_suffix": "keylight", "pixel_aspect": True,
        "project": {"bits_per_channel": 16, "working_space": None, "linear_blending": None},
        "layers": [
            {"role": "background", "name": "Background", "alpha": "ignore", "still": True, "from_plate": False,
             "help": "background image file or sequence folder"},
            {"role": "plate", "name": "Plate", "default": "frames", "alpha": "ignore"},
        ],
    },
}

# Keylight 1.2 ("Keylight 906") parameters by match name, read from AE 26.5. Menus count from 1:
# View 1 Source ... 5 Screen Matte, 8 Combined Matte, 9 Status, 10 Intermediate Result, 11 Final Result;
# Source Alpha 1 Ignore, 2 Add To Inside Mask, 3 Normal; Replace Method 1 None, 2 Source, 3 Hard, 4 Soft Colour.
# The garbage cut is not Keylight's Outside Mask (it leaves a thin line of partial alpha along the mask
# edge inside the screen); it is a shape layer used as the plate's alpha track matte, applied after Keylight.
KEYLIGHT = "Keylight 906"
KEYLIGHT_PARAMS = {
    "view": "0002", "screen_colour": "0004", "screen_gain": "0005", "screen_balance": "0006",
    "despill_bias": "0007", "alpha_bias": "0008", "lock_biases": "0009", "screen_preblur": "0010",
    "clip_black": "0012", "clip_white": "0013", "clip_rollback": "0014", "shrink_grow": "0015",
    "softness": "0016", "despot_black": "0017", "despot_white": "0018", "replace_method": "0019",
    "inside_mask": "0023", "inside_softness": "0024", "inside_invert": "0025", "source_alpha": "0028",
    "outside_mask": "0031", "outside_softness": "0032", "outside_invert": "0033",
}
VIEW = {"screen_matte": 5, "combined_matte": 8, "status": 9, "intermediate": 10, "final": 11}
# Other keying effects the round script may switch on; their parameters are also read from AE 26.5.
EXTRA_EFFECTS = {
    "Key Cleaner": ("ADBE KeyCleaner", {"edge_radius": "ADBE KeyCleaner-0006", "reduce_chatter": "ADBE KeyCleaner-0002",
                                         "alpha_contrast": "ADBE KeyCleaner-0016", "strength": "ADBE KeyCleaner-0001"}),
    "Spill": ("ADBE Spill2", {"method": "ADBE Spill2-0001", "suppression": "ADBE Spill2-1001",
                               "key_color": "ADBE Spill2-0003", "tolerance": "ADBE Spill2-0004"}),
}


def keylight_params(values):
    """{"clip_black": 20, ...} -> {"Keylight 906-0012": 20, ...}; colours become RGBA."""
    out = {}
    for name, value in values.items():
        if name not in KEYLIGHT_PARAMS:
            raise CompError(f"unknown Keylight parameter {name!r}; known: {', '.join(sorted(KEYLIGHT_PARAMS))}")
        if name.endswith("colour") or name.endswith("bias"):
            value = [float(v) for v in value][:3] + [1.0]
        out[f"{KEYLIGHT}-{KEYLIGHT_PARAMS[name]}"] = value
    return out


def parse_colour(value):
    """'0.36,0.62,0.37', '92,158,94' or a list -> [r, g, b] in 0..1."""
    parts = value.split(",") if isinstance(value, str) else list(value)
    try:
        rgb = [float(v) for v in parts]
    except (TypeError, ValueError):
        raise CompError(f"screen colour needs three numbers: {value!r}") from None
    if len(rgb) != 3 or min(rgb) < 0:
        raise CompError(f"screen colour needs three non-negative numbers: {value!r}")
    if max(rgb) > 1:
        rgb = [v / 255 for v in rgb]
    if max(rgb) > 1:
        raise CompError(f"screen colour is above 255: {value!r}")
    return rgb


def keylight_setup(contract, args, plate_height):
    """Keylight effects for the plate: a core pass (off until needed) and the edge pass, plus the garbage polygon."""
    settings = contract.get("keylight") or {}
    colour = args.screen_colour if args.screen_colour is not None else settings.get("screen_colour")
    if colour is None:
        raise CompError("pass --screen-colour or run keylight.py plan first (it writes keylight.screen_colour to shot.json)")
    colour = parse_colour(colour)
    garbage = settings.get("garbage")
    if garbage is not None:
        if not (isinstance(garbage, list) and len(garbage) >= 3 and all(len(p) == 2 for p in garbage)):
            raise CompError("keylight.garbage in shot.json must be a list of at least three [x, y] points")
        garbage = [[float(x), float(y)] for x, y in garbage]
    # Keylight's guide: balance about 50 for green screens and 95 for blue ones.
    balance = 95 if colour[2] > colour[1] else 50
    core = {"view": VIEW["intermediate"], "screen_colour": colour, "screen_balance": balance,
            "clip_black": 30, "clip_white": 60, "shrink_grow": -max(2, round(plate_height / 240))}
    edge = {"view": VIEW["final"], "screen_colour": colour, "screen_balance": balance, "source_alpha": 1}
    # Keylight's own despill leaves a screen cast in the soft edge. Advanced Spill Suppressor (Ultra) removes
    # it when its key colour is the pure screen hue; the measured, greyer screen colour only partly suppresses.
    spill = EXTRA_EFFECTS["Spill"][1]
    hue = [0.0, 0.0, 1.0, 1.0] if balance == 95 else [0.0, 1.0, 0.0, 1.0]
    return {
        "garbage": garbage,
        "effects": [
            {"name": "Keylight Core", "match": KEYLIGHT, "enabled": False, "params": keylight_params(core)},
            {"name": "Keylight Edge", "match": KEYLIGHT, "enabled": True, "params": keylight_params(edge)},
            {"name": "Key Cleaner", "match": EXTRA_EFFECTS["Key Cleaner"][0], "enabled": False, "params": {}},
            {"name": "Spill", "match": EXTRA_EFFECTS["Spill"][0], "enabled": True,
             "params": {spill["method"]: 2, spill["key_color"]: hue}},
        ],
    }


# Shown in After Effects only when the result file cannot be written.
MESSAGES = {
    "not_empty": "프로젝트에 이미 항목이 있어 아무것도 바꾸지 않았습니다. "
                 "File > New > New Project로 빈 프로젝트를 연 뒤 다시 실행하세요.",
    "not_adobe_color": "Project Settings > Color의 색 관리가 OCIO입니다. "
                       "Adobe로 바꾼 새 프로젝트에서 다시 실행하세요.",
    "done": "컴프를 만들었습니다. 저장은 File > Save As로 직접 하세요.",
    "failed": "컴프를 만들지 못했습니다. 이번 실행에서 추가한 항목과 바꾼 설정은 되돌렸습니다.",
    "no_receipt": "결과 기록(build_comp.result.json)은 쓰지 못했습니다. Preferences > Scripting & Expressions의 "
                  "'Allow Scripts to Write Files and Access Network'가 꺼져 있으면 기록만 빠집니다. "
                  "이 창의 내용을 에이전트에게 알려 주세요.",
}


class CompError(ValueError):
    pass


def parse_ratio(value, what):
    """30000/1001, 29.97, 24 or [30000, 1001] -> positive Fraction."""
    try:
        if isinstance(value, (list, tuple)) and len(value) == 2:
            ratio = Fraction(int(value[0]), int(value[1]))
        elif isinstance(value, (int, float, str)) and not isinstance(value, bool):
            ratio = Fraction(str(value).strip())
        else:
            raise ValueError
    except (ValueError, ZeroDivisionError):
        raise CompError(f"cannot read {what}: {value!r}") from None
    if ratio <= 0:
        raise CompError(f"{what} must be positive: {value!r}")
    return ratio


def describe_sequence(folder):
    """One contiguous, zero-padded image sequence in a folder -> (first file, frame count)."""
    files = [p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")]
    if not files:
        raise CompError(f"empty folder: {folder}")
    groups = {}
    for path in files:
        match = NUMBERED.match(path.name)
        if not match or match.group(3).lower() not in IMAGE_SUFFIXES:
            raise CompError(f"not a numbered image: {path}")
        prefix, digits, suffix = match.groups()
        groups.setdefault((prefix, len(digits), suffix), []).append((int(digits), path))
    if len(groups) != 1:
        raise CompError(f"keep one sequence per folder, same name, digit count and extension: {folder}")
    frames = sorted(next(iter(groups.values())))
    numbers = [number for number, _ in frames]
    first = numbers[0]
    if numbers != list(range(first, first + len(numbers))):
        missing = sorted(set(range(first, numbers[-1] + 1)) - set(numbers))
        raise CompError(f"missing frame numbers {missing[:5]}: {folder}")
    return frames[0][1], len(frames)


def describe(path, spec, start_frame, pixel_aspect):
    path = Path(path).expanduser().resolve()
    from_plate = spec.get("from_plate", True)
    layer = {"role": spec["role"], "name": spec["name"], "alpha": spec["alpha"], "enabled": spec.get("enabled", True),
             "start_frame": start_frame, "from_plate": from_plate,
             "pixel_aspect": float(pixel_aspect) if pixel_aspect and from_plate else None}
    if path.is_dir():
        first, count = describe_sequence(path)
        layer.update(kind="sequence", path=str(first), frames=count)
    elif path.is_file() and spec.get("still") and path.suffix.lower() in IMAGE_SUFFIXES:
        layer.update(kind="still", path=str(path), frames=None, start_frame=0)
    elif path.is_file():
        raise CompError(f"--{spec['role']} needs a sequence folder; extract movies to PNG frames with FFmpeg first: {path}")
    else:
        raise CompError(f"--{spec['role']} path not found: {path}")
    return layer


def read_contract(shot_dir, preset):
    path = shot_dir / preset["contract"]
    if not path.is_file():
        return {}
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CompError(f"cannot read {path}: {error}") from None
    if not isinstance(contract, dict):
        raise CompError(f"{path} must hold a JSON object")
    return contract


def build_job(args):
    preset = PRESETS[args.preset]
    shot = args.shot
    if not re.fullmatch(r"[^\W][\w.-]*", shot or ""):
        raise CompError(f"shot name: letters, digits, _ - . and no spaces: {shot!r}")
    shot_dir = Path(args.work).expanduser().resolve() / shot
    contract = read_contract(shot_dir, preset)
    fps_value = args.fps if args.fps is not None else contract.get("fps")
    if fps_value is None:
        raise CompError(f"pass --fps or put fps in {shot_dir / preset['contract']} (for example 30000/1001)")
    fps = parse_ratio(fps_value, "fps")
    pixel_aspect = None
    if preset["pixel_aspect"]:
        par_value = args.pixel_aspect if args.pixel_aspect is not None else contract.get("pixel_aspect")
        pixel_aspect = parse_ratio(par_value, "pixel aspect") if par_value is not None else None

    layers = []
    for spec in preset["layers"]:
        role = spec["role"]
        value = getattr(args, role)
        if value is None and spec.get("default"):
            value = shot_dir / spec["default"]
        if value is None:
            if spec.get("required"):
                raise CompError(f"--{role} is required")
            continue
        layers.append(describe(value, spec, getattr(args, f"{role}_start", 0), pixel_aspect))

    plate_index = next(i for i, layer in enumerate(layers) if layer["role"] == "plate")
    plate_frames = layers[plate_index]["frames"]
    for layer in layers:
        if layer["role"] == "plate" or layer["kind"] != "sequence" or not layer["from_plate"]:
            continue
        if layer["start_frame"] < 0 or layer["start_frame"] + layer["frames"] > plate_frames:
            raise CompError(f"{layer['name']}: start {layer['start_frame']} + {layer['frames']} frames "
                            f"does not fit the {plate_frames}-frame plate; check the start frame")

    project = preset["project"]
    key = next((layer for layer in layers if layer["role"] == "key"), None)
    if key and Path(key["path"]).suffix.lower() == ".exr":
        project = LINEAR_SRGB_32
    keylight = None
    if args.preset == "keylight":
        keylight = keylight_setup(contract, args, plate_image_height(layers[plate_index]["path"]))
    ae_dir = shot_dir / "ae"
    return {
        "job_id": uuid.uuid4().hex[:12],
        "shot": shot,
        "preset": args.preset,
        "comp_name": f"{shot}_{preset['comp_suffix']}",
        "folder_name": shot,
        "fps": float(fps),
        "fps_ratio": [fps.numerator, fps.denominator],
        "project": project,
        "layers": layers,
        "plate_index": plate_index,
        "keylight": keylight,
        "receipt": str(ae_dir / "build_comp.result.json"),
        "dialogs": not args.no_dialogs,
        "messages": MESSAGES,
    }


def plate_image_height(path):
    """Height from a PNG header (enough to scale the core erosion); other formats assume 1080."""
    with open(path, "rb") as stream:
        head = stream.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
        return int.from_bytes(head[20:24], "big")
    return 1080


def render_jsx(job):
    template = TEMPLATE.read_text(encoding="ascii")
    if template.count(PLACEHOLDER) != 1:
        raise CompError(f"{TEMPLATE} must contain {PLACEHOLDER} once")
    # ensure_ascii keeps the script ASCII; non-ASCII paths and messages become \u escapes.
    return template.replace(PLACEHOLDER, json.dumps(job, ensure_ascii=True))


def write_jsx(job):
    receipt = Path(job["receipt"])
    receipt.parent.mkdir(parents=True, exist_ok=True)
    jsx = receipt.with_name("build_comp.jsx")
    jsx.write_text(render_jsx(job), encoding="ascii", newline="\n")
    return jsx


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    presets = parser.add_subparsers(dest="preset", required=True, metavar="{" + ",".join(PRESETS) + "}")
    for name, preset in PRESETS.items():
        contract = preset["contract"]
        sub = presets.add_parser(name, help=preset["help"], description=preset["help"])
        sub.add_argument("--shot", required=True, help="work/<shot> folder name")
        sub.add_argument("--fps", help=f"rational FPS such as 30000/1001 (default: fps in {contract})")
        if preset["pixel_aspect"]:
            sub.add_argument("--pixel-aspect", help=f"pixel aspect such as 3/2 (default: pixel_aspect in {contract})")
        sub.add_argument("--work", default=str(ROOT / "work"), help="folder that holds <shot> (default: work/)")
        for spec in preset["layers"]:
            default = f"work/<shot>/{spec['default']}" if spec.get("default") else "none"
            sub.add_argument(f"--{spec['role']}", help=f"{spec.get('help', spec['name'])} (default: {default})")
            if spec["role"] != "plate":
                sub.add_argument(f"--{spec['role']}-start", type=int, default=0,
                                 help=f"comp frame of the first {spec['role']} frame (default: 0)")
        if name == "keylight":
            sub.add_argument("--screen-colour", help="screen colour as R,G,B in 0-1 or 0-255 "
                                                      "(default: keylight.screen_colour in shot.json)")
        sub.add_argument("--no-dialogs", action="store_true", help="no alert even when the result file cannot be written (automated checks)")
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0].startswith("-") and argv[0] not in ("-h", "--help"):
        argv = ["keying", *argv]  # the starter's original form: scripts/ae_comp.py --shot ... --key ...
    return parser.parse_args(argv)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    args = parse_args(argv)
    try:
        job = build_job(args)
        jsx = write_jsx(job)
    except (CompError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"JSX: {jsx}")
    print(f"comp: {job['comp_name']}  fps {job['fps_ratio'][0]}/{job['fps_ratio'][1]}  job {job['job_id']}")
    for layer in reversed(job["layers"]):
        span = "still" if layer["kind"] == "still" else f"{layer['frames']} frames at comp frame {layer['start_frame']}"
        print(f"  {layer['name']}: {span}  {layer['path']}")
    if job["keylight"]:
        effects = ", ".join(f"{e['name']}{'' if e['enabled'] else ' (off)'}" for e in job["keylight"]["effects"])
        print(f"  Plate effects: {effects}; garbage matte: {'yes' if job['keylight']['garbage'] else 'no'}")
    print("AE: File > New > New Project, then File > Scripts > Run Script File > build_comp.jsx")
    print("No message appears in AE; read the result file and match its job_id.")
    print(f"result: {job['receipt']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
