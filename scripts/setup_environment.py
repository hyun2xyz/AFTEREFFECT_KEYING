#!/usr/bin/env python3
"""Check, configure and install the local tools for this starter.

Runs with the Python standard library only, so it works before any package is
installed. It never edits PATH, global settings or applications outside this
repository. Lookup order for each tool: argument, environment variable,
tools.local.json, PATH, then known default install folders.
"""
import argparse
import glob
import json
import os
import platform
import shutil
import subprocess
import sys
import venv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "tools.local.json")
SUPPORTED_PYTHON = ((3, 12), (3, 13))

# Required command-line tools: name -> (environment variable, executable stem, version flag).
TOOLS = {
    "ffmpeg": ("FFMPEG_BINARY", "ffmpeg", "-version"),
    "ffprobe": ("FFPROBE_BINARY", "ffprobe", "-version"),
    "nvidia_smi": ("NVIDIA_SMI_BINARY", "nvidia-smi", "-L"),
}

# Tools that are reported but do not fail --check (for example a GPU utility).
OPTIONAL_TOOLS = {"nvidia_smi"}

# Known default install folders per OS, searched after PATH.
DEFAULT_TOOL_PATHS = {}

# Optional local HTTP services checked by --check (reported, never started).
SERVICES = {}

# Applications the student installs with their own account. Reported, not installed.
APPS = {
    "after_effects": {
        "Windows": ["C:/Program Files/Adobe/Adobe After Effects */Support Files/AfterFX.exe"],
        "Darwin": ["/Applications/Adobe After Effects */Adobe After Effects *.app"],
    },
    "corridorkey": {
        "Windows": ["%LOCALAPPDATA%/AFTEREFFECT_KEYING/CorridorKey2.0/infer.py"],
        "Linux": ["~/AFTEREFFECT_KEYING/CorridorKey2.0/infer.py"],
    },
}

IMPORT_CHECKS = ["numpy", "PIL"]


def venv_python():
    if os.name == "nt":
        return os.path.join(ROOT, ".venv", "Scripts", "python.exe")
    return os.path.join(ROOT, ".venv", "bin", "python")


def load_config(path=CONFIG):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def find_tool(name, explicit=None, environ=None, config=None):
    """Return (absolute path, source) for a tool, or (None, None)."""
    environ = os.environ if environ is None else environ
    config = load_config() if config is None else config
    env_name, stem, _ = TOOLS[name]
    candidates = [
        (explicit, "argument"),
        (environ.get(env_name), "environment"),
        (config.get(name), "tools.local.json"),
    ]
    for value, source in candidates:
        if value:
            path = os.path.abspath(os.path.expanduser(value))
            if os.path.isfile(path):
                return path, source
            return None, f"{source} points to a missing file: {path}"
    found = shutil.which(stem)
    if found:
        return os.path.abspath(found), "PATH"
    for pattern in DEFAULT_TOOL_PATHS.get(name, {}).get(platform.system(), []):
        matches = sorted(glob.glob(pattern))
        if matches:
            return os.path.abspath(matches[-1]), "default install folder"
    return None, None


def find_app(name, explicit=None, config=None):
    config = load_config() if config is None else config
    value = explicit or config.get(name)
    if value:
        path = os.path.abspath(os.path.expanduser(value))
        return (path, "configured") if os.path.exists(path) else (None, f"missing: {path}")
    for pattern in APPS[name].get(platform.system(), []):
        matches = sorted(glob.glob(os.path.expandvars(os.path.expanduser(pattern))))
        if matches:
            return os.path.abspath(matches[-1]), "default install folder"
    return None, None


def first_line(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        return None, str(error)
    text = (result.stdout or result.stderr).strip().splitlines()
    return (text[0] if text else ""), None if result.returncode == 0 else f"exit {result.returncode}"


def service_up(url, timeout=3):
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except OSError:
        return False


def python_ok(version=None):
    version = tuple((version or sys.version_info)[:2])
    return version in SUPPORTED_PYTHON


def check(args):
    problems = []
    print(f"Python {platform.python_version()} at {sys.executable}")
    if not python_ok():
        problems.append("Python 3.12 or 3.13 is required (see the setup document for your OS).")
    for name in TOOLS:
        path, source = find_tool(name, getattr(args, name, None))
        if not path:
            message = f"{name} not found" + (f" ({source})" if source else "")
            if name in OPTIONAL_TOOLS:
                print(f"{message} (optional)")
            else:
                problems.append(message)
            continue
        line, error = first_line([path, TOOLS[name][2]])
        if error:
            problems.append(f"{name} at {path} failed to run: {error}")
        else:
            print(f"{name}: {path} [{source}] {line}")
    for name in APPS:
        path, source = find_app(name, getattr(args, name, None))
        if path:
            print(f"{name}: {path} [{source}]")
        else:
            print(f"{name}: not detected. Install it as the setup document describes, then pass --{name.replace('_', '-')}.")
    for name, url in SERVICES.items():
        print(f"{name}: {'reachable' if service_up(url) else 'not running'} at {url}")
    python = venv_python()
    if os.path.isfile(python):
        code = "import " + ", ".join(IMPORT_CHECKS)
        _, error = first_line([python, "-c", code])
        if error:
            problems.append(f".venv is missing packages ({error}); run --install")
        else:
            print(f".venv: {python} imports {', '.join(IMPORT_CHECKS)}")
    else:
        print(".venv: not created yet (run --install after tools are found).")
    for problem in problems:
        print(f"MISSING: {problem}", file=sys.stderr)
    return 1 if problems else 0


def configure(args):
    config = load_config()
    for name in TOOLS:
        path, source = find_tool(name, getattr(args, name, None), config=config)
        if path:
            config[name] = path
        else:
            print(f"{name}: not found ({source or 'not on PATH'}); left unset.", file=sys.stderr)
    for name in APPS:
        path, _ = find_app(name, getattr(args, name, None), config=config)
        if path:
            config[name] = path
    with open(CONFIG, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"Wrote {CONFIG}")
    return 0


def install(_args):
    if not python_ok():
        print("Run --install with Python 3.12 or 3.13.", file=sys.stderr)
        return 1
    if not os.path.isfile(venv_python()):
        venv.EnvBuilder(with_pip=True).create(os.path.join(ROOT, ".venv"))
    requirements = os.path.join(ROOT, "requirements.txt")
    result = subprocess.run([venv_python(), "-m", "pip", "install", "-r", requirements])
    return result.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report tools; change nothing")
    mode.add_argument("--configure", action="store_true", help="save found absolute paths to tools.local.json")
    mode.add_argument("--install", action="store_true", help="create .venv and install requirements.txt")
    for name in TOOLS:
        parser.add_argument(f"--{name}", help=f"absolute path to {name}")
    for name in APPS:
        parser.add_argument(f"--{name.replace('_', '-')}", dest=name, help=f"absolute path to {name}")
    args = parser.parse_args(argv)
    if args.check:
        return check(args)
    if args.configure:
        return configure(args)
    return install(args)


if __name__ == "__main__":
    sys.exit(main())
