"""Dump a .kicad_pcb to JSON for the viewer and checker. Runs under KiCad's Python (needs pcbnew).

    board_dump.py <board.kicad_pcb> <out.json>

All coordinates are KiCad board coordinates in mm (y grows downwards), as shown in the PCB editor
and in kicad-cli DRC reports.
"""
import json
import sys

import pcbnew

MM = pcbnew.ToMM
MAX_ERR = pcbnew.FromMM(0.005)


def poly_points(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        out.append([[round(MM(o.CPoint(k).x), 4), round(MM(o.CPoint(k).y), 4)] for k in range(o.PointCount())])
    return out


def item_poly(item, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps, layer, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
    return poly_points(ps)


def bbox(box):
    return [round(MM(box.GetLeft()), 4), round(MM(box.GetTop()), 4), round(MM(box.GetRight()), 4), round(MM(box.GetBottom()), 4)]


def union(boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def netclass(item):
    try:
        return item.GetNetClassName()     # GetEffectiveNetClass() comes back unwrapped in KiCad 10's bindings
    except Exception:
        return ""


def text_info(t, layer_name):
    return {"text": t.GetShownText(True) if hasattr(t, "GetShownText") else t.GetText(), "layer": layer_name,
            "visible": t.IsVisible(), "height": round(MM(t.GetTextHeight()), 4),
            "width": round(MM(t.GetTextWidth()), 4), "thickness": round(MM(t.GetTextThickness()), 4),
            "bbox": bbox(t.GetBoundingBox())}


def dump(path):
    b = pcbnew.LoadBoard(path)
    if b is None:
        sys.exit(f"KiCad couldn't load {path}")
    ln = b.GetLayerName
    silk_layers = (pcbnew.F_SilkS, pcbnew.B_SilkS)
    fab_layers = (pcbnew.F_Fab, pcbnew.B_Fab)

    outline = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outline, False)
    out = {
        "file": path,
        "board": {
            "thickness": round(MM(b.GetDesignSettings().GetBoardThickness()), 4),
            "copper_layers": b.GetCopperLayerCount(),
            "bbox": bbox(b.GetBoardEdgesBoundingBox()),
            "outline": poly_points(outline),
        },
        "footprints": [], "tracks": [], "vias": [], "zones": [], "texts": [], "silk": [],
    }

    for fp in b.GetFootprints():
        side = "B" if fp.IsFlipped() else "F"
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd)
        attrs = fp.GetAttributes()
        fields = {f.GetName(): f.GetText() for f in fp.GetFields()}
        silk, fab = [], []
        for g in fp.GraphicalItems():
            layer = g.GetLayer()
            if g.GetClass() in ("PCB_TEXT", "PCB_FIELD"):
                if layer in silk_layers:
                    out["texts"].append(dict(text_info(g, ln(layer)), ref=fp.GetReference()))
                continue
            if layer in silk_layers:
                silk.append({"layer": ln(layer), "width": round(MM(g.GetWidth()), 4), "poly": item_poly(g, layer)})
            elif layer in fab_layers:
                fab.append(bbox(g.GetBoundingBox()))
        for f in fp.GetFields():
            if f.GetLayer() in silk_layers and f.IsVisible():
                out["texts"].append(dict(text_info(f, ln(f.GetLayer())), ref=fp.GetReference(), field=f.GetName()))
        pads = []
        for p in fp.Pads():
            q = p.GetPosition()
            a = p.GetAttribute()
            kind = {pcbnew.PAD_ATTRIB_PTH: "PTH", pcbnew.PAD_ATTRIB_NPTH: "NPTH",
                    pcbnew.PAD_ATTRIB_SMD: "SMD", pcbnew.PAD_ATTRIB_CONN: "CONN"}.get(a, "?")
            layer = pcbnew.B_Cu if (side == "B" and kind in ("SMD", "CONN")) else pcbnew.F_Cu
            d = p.GetDrillSize()
            copper = p.IsOnCopperLayer()          # paste-only apertures (e.g. QFN paste windows) aren't copper
            pads.append({
                "num": p.GetNumber(), "net": p.GetNetname(), "netclass": netclass(p), "kind": kind,
                "x": round(MM(q.x), 4), "y": round(MM(q.y), 4), "bbox": bbox(p.GetBoundingBox()),
                "copper": copper,
                "poly": item_poly(p, layer) if copper and (kind != "NPTH" or p.GetSize(pcbnew.F_Cu).x > d.x) else [],
                "drill": [round(MM(d.x), 4), round(MM(d.y), 4)] if kind in ("PTH", "NPTH") else None,
                "slot": kind in ("PTH", "NPTH") and p.GetDrillShape() == pcbnew.PAD_DRILL_SHAPE_OBLONG,
            })
        ref_field = fp.Reference()
        out["footprints"].append({
            "ref": fp.GetReference(), "value": fp.GetValue(), "lib": fp.GetFPIDAsString(),
            "x": round(MM(fp.GetPosition().x), 4), "y": round(MM(fp.GetPosition().y), 4),
            "rot": round(fp.GetOrientationDegrees(), 3), "side": side,
            "smd": bool(attrs & pcbnew.FP_SMD), "tht": bool(attrs & pcbnew.FP_THROUGH_HOLE),
            "exclude_from_bom": bool(attrs & pcbnew.FP_EXCLUDE_FROM_BOM),
            "exclude_from_pos": bool(attrs & pcbnew.FP_EXCLUDE_FROM_POS_FILES),
            "dnp": bool(fp.IsDNP()) if hasattr(fp, "IsDNP") else False,
            "fields": fields,
            "courtyard": bbox(cy.BBox()) if cy.OutlineCount() else None,
            "body": union(fab),
            "label": {"bbox": bbox(ref_field.GetBoundingBox()), "visible": ref_field.IsVisible(),
                      "layer": ln(ref_field.GetLayer())},
            "silk": silk, "pads": pads,
        })

    for t in b.GetTracks():
        cls = t.GetClass()
        if cls == "PCB_VIA":
            q = t.GetPosition()
            out["vias"].append({"x": round(MM(q.x), 4), "y": round(MM(q.y), 4), "net": t.GetNetname(),
                                "dia": round(MM(t.GetWidth(pcbnew.F_Cu)), 4), "drill": round(MM(t.GetDrillValue()), 4)})
        elif cls in ("PCB_TRACK", "PCB_ARC"):
            out["tracks"].append({"x1": round(MM(t.GetStart().x), 4), "y1": round(MM(t.GetStart().y), 4),
                                  "x2": round(MM(t.GetEnd().x), 4), "y2": round(MM(t.GetEnd().y), 4),
                                  "width": round(MM(t.GetWidth()), 4), "layer": ln(t.GetLayer()),
                                  "front": t.GetLayer() == pcbnew.F_Cu, "net": t.GetNetname()})

    for z in b.Zones():
        layers = [ln(l) for l in z.GetLayerSet().Seq()]
        out["zones"].append({"net": z.GetNetname(), "layers": layers, "keepout": z.GetIsRuleArea(),
                             "outline": poly_points(z.Outline())})

    for d in b.GetDrawings():
        layer = d.GetLayer()
        if layer in silk_layers:
            if d.GetClass() == "PCB_TEXT":
                out["texts"].append(dict(text_info(d, ln(layer)), ref=None))
            else:
                out["silk"].append({"layer": ln(layer), "width": round(MM(d.GetWidth()), 4), "poly": item_poly(d, layer)})
    return out


if __name__ == "__main__":
    data = dump(sys.argv[1])
    with open(sys.argv[2], "w") as f:
        json.dump(data, f)
