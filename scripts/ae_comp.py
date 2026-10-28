#!/usr/bin/env python3
"""Write the After Effects JSX that builds one shot's comp from the plate and result layers.

The JSX goes to work/<shot>/ae/build_comp.jsx. The student opens a new, empty project
and runs it with File > Scripts > Run Script File; it writes build_comp.result.json
next to itself. A sequence is a folder of contiguously numbered, zero-padded frames.
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

# Repository preset: docs/rules.md section 7. Color settings stay as the student set them.
CONTRACT = "shot.json"
COMP_SUFFIX = "key"
PROJECT = {"bits_per_channel": 16, "working_space": None, "linear_blending": None}
PIXEL_ASPECT_OPTION = True
# Bottom to top. The first layer is the plate; it sets the comp size and length.
# default: folder under work/<shot>/ used when the option is omitted.
# from_plate (default true): rendered from the plate, so same size and within its frames.
LAYERS = [
    {"role": "plate", "name": "Plate (reference)", "default": "frames", "alpha": "ignore", "enabled": False},
    {"role": "background", "name": "Background", "alpha": "ignore", "still": True, "from_plate": False,
     "help": "background image file or sequence folder"},
    {"role": "key", "name": "Key", "alpha": "straight", "required": True,
     "help": "keyed straight RGBA sequence, such as the CorridorKey cutout"},
]

# Shown in After Effects.
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
    layer = {"name": spec["name"], "alpha": spec["alpha"], "enabled": spec.get("enabled", True),
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


def read_contract(shot_dir):
    path = shot_dir / CONTRACT
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
    shot = args.shot
    if not re.fullmatch(r"[^\W][\w.-]*", shot or ""):
        raise CompError(f"shot name: letters, digits, _ - . and no spaces: {shot!r}")
    shot_dir = Path(args.work).expanduser().resolve() / shot
    contract = read_contract(shot_dir)
    fps_value = args.fps if args.fps is not None else contract.get("fps")
    if fps_value is None:
        raise CompError(f"pass --fps or put fps in {shot_dir / CONTRACT} (for example 30000/1001)")
    fps = parse_ratio(fps_value, "fps")
    pixel_aspect = None
    if PIXEL_ASPECT_OPTION:
        par_value = args.pixel_aspect if args.pixel_aspect is not None else contract.get("pixel_aspect")
        pixel_aspect = parse_ratio(par_value, "pixel aspect") if par_value is not None else None

    layers = []
    for spec in LAYERS:
        role = spec["role"]
        value = getattr(args, role)
        if value is None and spec.get("default"):
            value = shot_dir / spec["default"]
        if value is None:
            if spec.get("required"):
                raise CompError(f"--{role} is required")
            continue
        layers.append(describe(value, spec, getattr(args, f"{role}_start", 0), pixel_aspect))

    plate_frames = layers[0]["frames"]
    for layer in layers[1:]:
        if layer["kind"] != "sequence" or not layer["from_plate"]:
            continue
        if layer["start_frame"] < 0 or layer["start_frame"] + layer["frames"] > plate_frames:
            raise CompError(f"{layer['name']}: start {layer['start_frame']} + {layer['frames']} frames "
                            f"does not fit the {plate_frames}-frame plate; check the start frame")

    ae_dir = shot_dir / "ae"
    return {
        "job_id": uuid.uuid4().hex[:12],
        "shot": shot,
        "comp_name": f"{shot}_{COMP_SUFFIX}",
        "folder_name": shot,
        "fps": float(fps),
        "fps_ratio": [fps.numerator, fps.denominator],
        "project": PROJECT,
        "layers": layers,
        "receipt": str(ae_dir / "build_comp.result.json"),
        "dialogs": not args.no_dialogs,
        "messages": MESSAGES,
    }


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
    parser.add_argument("--shot", required=True, help="work/<shot> folder name")
    parser.add_argument("--fps", help=f"rational FPS such as 30000/1001 (default: fps in {CONTRACT})")
    if PIXEL_ASPECT_OPTION:
        parser.add_argument("--pixel-aspect", help=f"pixel aspect such as 3/2 (default: pixel_aspect in {CONTRACT})")
    parser.add_argument("--work", default=str(ROOT / "work"), help="folder that holds <shot> (default: work/)")
    for spec in LAYERS:
        default = f"work/<shot>/{spec['default']}" if spec.get("default") else "none"
        parser.add_argument(f"--{spec['role']}", help=f"{spec.get('help', spec['name'])} (default: {default})")
        if spec is not LAYERS[0]:
            parser.add_argument(f"--{spec['role']}-start", type=int, default=0,
                                help=f"comp frame of the first {spec['role']} frame (default: 0)")
    parser.add_argument("--no-dialogs", action="store_true", help="no alert at the end (automated checks)")
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
    print("AE: File > New > New Project, then File > Scripts > Run Script File > build_comp.jsx")
    print(f"result: {job['receipt']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
