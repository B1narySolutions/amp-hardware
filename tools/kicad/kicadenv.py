"""Find KiCad's Python and kicad-cli, and run them.

The tools run under the system python3 (which has matplotlib). Anything that needs `import pcbnew`
runs in a subprocess under KiCad's own Python, found here.

Override the search with the KICAD_PYTHON and KICAD_CLI environment variables.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

_PYTHON_CANDIDATES = [
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3",
    r"C:\Program Files\KiCad\10.0\bin\python.exe",
    r"C:\Program Files\KiCad\9.0\bin\python.exe",
    "/usr/bin/python3",
]
_CLI_CANDIDATES = [
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
    r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
    r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
]


def _has_pcbnew(python):
    try:
        r = subprocess.run([python, "-c", "import pcbnew"], capture_output=True, timeout=60)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def kicad_python():
    env = os.environ.get("KICAD_PYTHON")
    if env:
        return env
    for p in _PYTHON_CANDIDATES:
        if os.path.exists(p) and _has_pcbnew(p):
            return p
    sys.exit("Can't find a Python that imports pcbnew. Set KICAD_PYTHON to KiCad's bundled python.")


def kicad_cli():
    env = os.environ.get("KICAD_CLI")
    if env:
        return env
    for p in _CLI_CANDIDATES:
        if os.path.exists(p):
            return p
    p = shutil.which("kicad-cli")
    if p:
        return p
    sys.exit("Can't find kicad-cli. Set KICAD_CLI to its path.")


def run_pcbnew_script(script, *args):
    """Run one of the pcbnew scripts in this folder under KiCad's Python. Returns stdout."""
    r = subprocess.run([kicad_python(), os.path.join(HERE, script), *args], capture_output=True, text=True)
    if r.returncode != 0:
        noise = ("wxApp", "stdpbase", "swig/python detected a memory leak")
        err = "\n".join(l for l in r.stderr.splitlines() if not any(n in l for n in noise))
        sys.exit(f"{script} failed:\n{err}")
    return r.stdout


def run_drc(board, extra=(), out=None):
    """Run kicad-cli DRC on a board and return the parsed JSON report."""
    own = out is None
    if own:
        fd, out = tempfile.mkstemp(suffix=".json")
        os.close(fd)
    try:
        subprocess.run([kicad_cli(), "pcb", "drc", "--format", "json", "--severity-all", *extra, "-o", out, board],
                       capture_output=True, text=True)
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            sys.exit(f"kicad-cli drc produced no report for {board}")
        with open(out) as f:
            return json.load(f)
    finally:
        if own and os.path.exists(out):
            os.remove(out)
