"""Find KiCad's Python and kicad-cli, and run them.

The tools run under the system python3 (which has matplotlib). Anything that needs `import pcbnew`
runs in a subprocess under KiCad's own Python, found here.

Override the search with the KICAD_PYTHON and KICAD_CLI environment variables.
"""
import json
import os
import re
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


_NGSPICE_CANDIDATES = [
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/libngspice.0.dylib",
    r"C:\Program Files\KiCad\10.0\bin\ngspice.dll",
    r"C:\Program Files\KiCad\9.0\bin\ngspice.dll",
    "/usr/lib/x86_64-linux-gnu/libngspice.so.0",
    "/usr/lib/libngspice.so.0",
    "/opt/homebrew/lib/libngspice.dylib",
    "/usr/local/lib/libngspice.dylib",
]


def ngspice_lib():
    """The ngspice shared library KiCad's simulator uses (or NGSPICE_LIB). None if there isn't one."""
    env = os.environ.get("NGSPICE_LIB")
    if env:
        return env
    for p in _NGSPICE_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


_FOOTPRINT_DIRS = [
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints",
    r"C:\Program Files\KiCad\10.0\share\kicad\footprints",
    r"C:\Program Files\KiCad\9.0\share\kicad\footprints",
    "/usr/share/kicad/footprints",
    "/usr/local/share/kicad/footprints",
]


def stock_footprint_dir():
    """KiCad's bundled footprint libraries (what ${KICAD10_FOOTPRINT_DIR} points at)."""
    for var in ("KICAD10_FOOTPRINT_DIR", "KICAD9_FOOTPRINT_DIR", "KICAD_FOOTPRINT_DIR"):
        if os.environ.get(var):
            return os.environ[var]
    for d in _FOOTPRINT_DIRS:
        if os.path.isdir(d):
            return d
    return None


def _global_fp_tables():
    home = os.path.expanduser("~")
    for ver in ("10.0", "9.0"):
        for base in (os.path.join(home, "Library", "Preferences", "kicad"),
                     os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config")), "kicad"),
                     os.path.join(os.environ.get("APPDATA", ""), "kicad")):
            p = os.path.join(base, ver, "fp-lib-table")
            if os.path.isfile(p):
                yield p


def _expand(uri, project_dir):
    def sub(m):
        var = m.group(1)
        if var == "KIPRJMOD":
            return project_dir
        if os.environ.get(var):
            return os.environ[var]
        if var.endswith("_FOOTPRINT_DIR"):
            return stock_footprint_dir() or m.group(0)
        return m.group(0)
    return os.path.normpath(re.sub(r"\$\{([^}]+)\}", sub, uri))


def _table_lookup(table, nickname, project_dir, seen):
    if table in seen or not os.path.isfile(table):
        return None
    seen.add(table)
    with open(table) as f:
        text = f.read()
    for m in re.finditer(r'\(lib\s+\(name\s+"([^"]+)"\)\s*\(type\s+"([^"]+)"\)\s*\(uri\s+"([^"]+)"\)', text):
        name, kind, uri = m.groups()
        path = _expand(uri, project_dir)
        if kind == "Table":
            found = _table_lookup(path, nickname, project_dir, seen)
            if found:
                return found
        elif name == nickname:
            return path
    return None


def footprint_lib_dir(nickname, project_dir):
    """Resolve a footprint library nickname (the part before ':' in "Lib:Footprint") to its .pretty folder.

    Looks in the project's fp-lib-table, then the user's global table (following KiCad 10's nested
    "Table" entries), then KiCad's stock footprint folder. A path to a .pretty folder is returned as is.
    """
    if os.path.isdir(nickname):
        return nickname
    seen = set()
    for table in [os.path.join(project_dir, "fp-lib-table"), *_global_fp_tables()]:
        found = _table_lookup(table, nickname, project_dir, seen)
        if found:
            return found
    stock = stock_footprint_dir()
    if stock and os.path.isdir(os.path.join(stock, nickname + ".pretty")):
        return os.path.join(stock, nickname + ".pretty")
    raise KeyError(f"footprint library {nickname!r} isn't in the project or global fp-lib-table")


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
