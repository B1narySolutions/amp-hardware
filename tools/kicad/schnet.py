"""Read what the schematic says about each part: its footprint, value, fields, symbol link and pin nets.

    import schnet
    parts = schnet.load("audio-board/rev2/seed3-carrier.kicad_pcb")   # the .kicad_sch next to the board
    parts["R21"]["footprint"]      # "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder"
    parts["R21"]["pins"]["2"]      # "/LINE_REF"
    parts["R21"]["path"]           # "/e812de32-...": what the board stores to link the footprint to its symbol

It asks kicad-cli for a netlist rather than parsing the schematic, so hierarchical sheets, multi-unit
symbols and KiCad's own net naming (including "unconnected-(...)" nets) come out exactly as KiCad's
"Update PCB from Schematic" would see them. Standard library only, so it runs under any Python.
"""
import os
import re
import subprocess
import tempfile

import kicadenv

_TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def _parse(text):
    stack, cur = [], []
    for tok in _TOKEN.findall(text):
        if tok == "(":
            stack.append(cur)
            cur = []
        elif tok == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        elif tok.startswith('"'):
            cur.append(bytes(tok[1:-1], "utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8"))
        else:
            cur.append(tok)
    return cur[0]


def _find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def _one(node, key, default=None):
    hits = _find(node, key)
    if not hits:
        return default
    rest = hits[0][1:]
    return rest[0] if len(rest) == 1 and not isinstance(rest[0], list) else rest


def schematic_for(board_path):
    sch = os.path.splitext(board_path)[0] + ".kicad_sch"
    return sch if os.path.isfile(sch) else None


def load(board_path):
    """Parts in the schematic next to a board, keyed by reference. None if there is no schematic."""
    sch = schematic_for(board_path)
    if not sch:
        return None
    fd, out = tempfile.mkstemp(suffix=".net")
    os.close(fd)
    try:
        r = subprocess.run([kicadenv.kicad_cli(), "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out, sch],
                           capture_output=True, text=True)
        if r.returncode != 0 or os.path.getsize(out) == 0:
            raise RuntimeError(f"kicad-cli couldn't export a netlist from {sch}: {r.stderr.strip()}")
        with open(out, encoding="utf-8") as f:
            tree = _parse(f.read())
    finally:
        os.remove(out)

    parts = {}
    for comp in _find(_find(tree, "components")[0], "comp"):
        ref = _one(comp, "ref")
        fields = {}
        for fl in _find(_one(comp, "fields", []) and _find(comp, "fields")[0], "field"):
            name = _one(fl, "name")
            if name not in ("Footprint",):
                fields[name] = fl[2] if len(fl) > 2 and not isinstance(fl[2], list) else ""
        props = {_one(p, "name"): _one(p, "value", "") for p in _find(comp, "property")}
        sheetpath = _find(comp, "sheetpath")[0]
        names, stamps = _one(sheetpath, "names"), _one(sheetpath, "tstamps")
        ids = _find(comp, "tstamps")[0][1:]
        parts[ref] = {
            "ref": ref,
            "value": _one(comp, "value", ""),
            "footprint": _one(comp, "footprint", ""),
            "fields": fields,
            "path": stamps.rstrip("/") + "/" + ids[0],
            "sheetname": names,
            "sheetfile": props.get("Sheetfile", ""),
            "dnp": "dnp" in props,
            "exclude_from_bom": "exclude_from_bom" in props,
            "pins": {},
            "pinfunctions": {},
            "pintypes": {},
        }
    for net in _find(_find(tree, "nets")[0], "net"):
        name = _one(net, "name")
        for node in _find(net, "node"):
            ref, pin = _one(node, "ref"), _one(node, "pin")
            if ref in parts:
                parts[ref]["pins"][pin] = name
                parts[ref]["pinfunctions"][pin] = _one(node, "pinfunction", "")
                parts[ref]["pintypes"][pin] = _one(node, "pintype", "")
    return parts
