"""Incremental, scripted edits to a KiCad board. Import it from a script run under KiCad's Python.

    import sys; sys.path.insert(0, "tools/kicad")
    from boardedit import Board

    b = Board("audio-board/rev2/seed3-carrier.kicad_pcb")
    b.place("R1", 127.86, 85.4, rot=90)                  # mm, degrees; immediate
    b.track("/VREF", [b.pad("R6", "2"), b.pad("R1", "2")], width=0.25)
    b.via(124.6, 87.75, "GND")
    b.gnd_via("C7", "1", dx=0, dy=1.6)                   # via plus a short stub from the pad
    b.set_pad_net("A1", "23", "/HP_DETECT")              # creates the net if it's new
    b.set_pad_unconnected("A1", "34")                    # KiCad's "unconnected-(A1-<pin>-Pad34)" net
    b.remove_tracks(nets=["/VREF"])                      # removes only what the filter names
    b.replace_footprint("J5", x=185.4, y=69.0, rot=90)   # footprint, fields and nets from the schematic
    b.add_footprint("R21", 179.3, 66.9)                  # a part that's in the schematic but not the board
    b.remove_footprint("FB1")                            # and the copper hanging off its pads
    b.set_field("R9", "Value", "10k")
    b.text("LINE+", 185.4, 71.75)                        # free silkscreen text, 1.0 / 0.15 mm by default
    b.auto_labels(["R1", "R6"])                          # references beside their parts
    b.save()                                             # writes the board, then refills zones

All lengths are mm in KiCad board coordinates (y grows downwards). Rotation follows KiCad: +90 is
counter-clockwise, so a 2-pad part at rot 90 has pad 1 below pad 2, at -90 pad 1 above.

Why the queue: in KiCad 10's Python bindings, once anything is added to or removed from the board,
footprints, pads and nets read afterwards come back as bare SwigPyObjects. So Board reads everything it
needs first, applies placements immediately (those are safe), and applies every add and remove in
save(), after label placement and track selection have done their reads. The breakage lasts for the
whole process, even for boards loaded later, so use one Board per process and nothing pcbnew after
save(). FindNet() is also unreliable, so nets come from the pads, tracks and zones that use them.
New footprints are loaded from their libraries when you call add_footprint/replace_footprint (a read),
held until save(), and only then added to the board.

Footprints added or replaced are linked to their schematic symbols the way KiCad's "Update PCB from
Schematic" does it: footprint, value, fields, symbol path, sheet and pad nets come from a kicad-cli
netlist of the .kicad_sch next to the board (schnet.py). Anything you pass explicitly wins.
"""
import os
import subprocess
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicadenv  # noqa: E402

MM, TOMM = pcbnew.FromMM, pcbnew.ToMM


def _poly_points(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        out.append([(TOMM(o.CPoint(k).x), TOMM(o.CPoint(k).y)) for k in range(o.PointCount())])
    return out


def _rect_hits_poly(rect, poly):
    l, t, r, b = rect
    if any(l < x < r and t < y < b for x, y in poly):
        return True
    def inside(px, py):
        hit = False
        for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
            if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
                hit = not hit
        return hit
    if any(inside(x, y) for x, y in ((l, t), (r, t), (r, b), (l, b))):
        return True
    edges = [((l, t), (r, t)), ((r, t), (r, b)), ((r, b), (l, b)), ((l, b), (l, t))]
    def cross(o, a, c):
        return (a[0] - o[0]) * (c[1] - o[1]) - (a[1] - o[1]) * (c[0] - o[0])
    for a, c in zip(poly, poly[1:] + poly[:1]):
        for p1, p2 in edges:
            d1, d2, d3, d4 = cross(a, c, p1), cross(a, c, p2), cross(p1, p2, a), cross(p1, p2, c)
            if (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0):
                return True
    return False


class Board:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        if not os.path.isfile(self.path):
            raise FileNotFoundError(self.path)
        self.board = pcbnew.LoadBoard(self.path)
        self.fps = {fp.GetReference(): fp for fp in self.board.GetFootprints()}
        self.nets = {}
        for fp in self.fps.values():
            for p in fp.Pads():
                self.nets.setdefault(p.GetNetname(), p.GetNet())
        for t in self.board.GetTracks():
            self.nets.setdefault(t.GetNetname(), t.GetNet())
        for z in self.board.Zones():
            self.nets.setdefault(z.GetNetname(), z.GetNet())
        self._tracks, self._vias, self._removes, self._net_changes = [], [], [], []
        self._labels, self._auto = {}, None
        self._moved = []
        self._saved = False
        self._loaded = dict(self.fps)           # footprints on the board as loaded (removed ones included)
        self._sch = None                        # schematic parts, read on first use
        self._added = {}                        # ref -> new FOOTPRINT, added in save()
        self._added_pads = {}                   # ref -> [(pad, net)] for the new footprints
        self._removed = []                      # (ref, FOOTPRINT, remove its tracks?)
        self._pending_nets = set()              # nets that save() will create
        self._texts, self._text_removes, self._text_moved = [], [], []

    # ------------------------------------------------------------ reads
    def _fp(self, ref):
        self._check()
        if ref not in self.fps:
            raise KeyError(f"no footprint {ref!r} on {os.path.basename(self.path)}")
        return self.fps[ref]

    def _pad(self, ref, num):
        for p in self._fp(ref).Pads():
            if p.GetNumber() == str(num):
                return p
        raise KeyError(f"{ref} has no pad {num!r}")

    def pad(self, ref, num):
        """(x, y) of a pad centre, reflecting any place() calls so far."""
        q = self._pad(ref, num).GetPosition()
        return (TOMM(q.x), TOMM(q.y))

    def pad_net(self, ref, num):
        return self._pad(ref, num).GetNetname()

    def position(self, ref):
        fp = self._fp(ref)
        return (TOMM(fp.GetPosition().x), TOMM(fp.GetPosition().y), fp.GetOrientationDegrees())

    def _layer(self, name):
        fixed = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu,
                 "F.SilkS": pcbnew.F_SilkS, "B.SilkS": pcbnew.B_SilkS, "F.Silkscreen": pcbnew.F_SilkS,
                 "B.Silkscreen": pcbnew.B_SilkS, "F.Fab": pcbnew.F_Fab, "B.Fab": pcbnew.B_Fab}
        if name in fixed:
            return fixed[name]
        lid = self.board.GetLayerID(name)
        if lid < 0:
            raise KeyError(f"no layer {name!r}")
        return lid

    def _net(self, name):
        if name in self._pending_nets:
            return None
        if name not in self.nets:
            raise KeyError(f"no net {name!r} on the board (nets come from pads, tracks and zones that use them, "
                           "or from set_pad_net / add_footprint / replace_footprint)")
        return self.nets[name]

    def _schematic(self, required):
        if self._sch is None:
            import schnet
            self._sch = schnet.load(self.path) or {}
        if required and not self._sch:
            raise FileNotFoundError(f"no schematic next to {os.path.basename(self.path)}; pass link=False and "
                                    "give footprint= and nets= yourself")
        return self._sch

    def _unconnected_name(self, ref, num, pin_function=""):
        part = (self._sch or {}).get(ref)
        if part and part["pins"].get(num, "").startswith("unconnected-"):
            return part["pins"][num]
        pin = pin_function
        if pin.endswith("_" + num):              # pin functions carry a _<number> suffix KiCad drops here
            pin = pin[: -len(num) - 1]
        return f"unconnected-({ref}-{pin}-Pad{num})" if pin else f"unconnected-({ref}-Pad{num})"

    # ------------------------------------------------------------ immediate edits
    def place(self, ref, x, y, rot=None, side=None):
        """Move a footprint (mm), optionally rotate it (degrees) and set its side ("F" or "B")."""
        fp = self._fp(ref)
        if side and (side == "B") != fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        if rot is not None:
            fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        self._moved.append(ref)

    # ------------------------------------------------------------ queued edits (applied in save)
    def track(self, net, points, width=0.25, layer="F.Cu"):
        """A polyline of track segments through points [(x, y), ...]."""
        self._net(net)
        self._tracks.append((net, [tuple(p) for p in points], width, self._layer(layer)))

    def via(self, x, y, net="GND", dia=0.6, drill=0.3):
        self._net(net)
        self._vias.append((x, y, net, dia, drill))

    def gnd_via(self, ref, num, dx, dy, width=0.5, net="GND", dia=0.6, drill=0.3):
        """A via at an offset from a pad, joined to it by a short stub on F.Cu."""
        x, y = self.pad(ref, num)
        self.via(x + dx, y + dy, net, dia, drill)
        self.track(net, [(x, y), (x + dx, y + dy)], width)
        return (x + dx, y + dy)

    def set_pad_net(self, ref, num, net):
        """Connect a pad to a net (created if new), or leave it unconnected with net=None."""
        self._pad(ref, num)
        if ref in self._added:
            raise ValueError(f"{ref} is a new footprint: give its nets to add_footprint/replace_footprint")
        if net is not None and net not in self.nets:
            self._pending_nets.add(net)
        self._net_changes.append((ref, str(num), net))

    def set_pad_unconnected(self, ref, num):
        """Put a pad on KiCad's own no-connect net, "unconnected-(<ref>-<pin name>-Pad<num>)", as the schematic
        names it when the pin is unconnected there (e.g. a pin that just got a no-connect flag)."""
        self.set_pad_net(ref, num, None)

    def set_field(self, ref, name, value, visible=None):
        """Set a footprint field ("Value", "LCSC", ...). A field the footprint didn't have is added hidden.
        Immediate, like place(). The schematic should say the same, or parity reports the difference."""
        fp = self._fp(ref)
        if name == "Reference":
            raise ValueError("rename a part in the schematic, then add_footprint/replace_footprint it")
        if name == "Value":
            fp.SetValue(value)
        else:
            if not fp.HasField(name) and visible is None:
                visible = False
            fp.SetField(name, value)
        if visible is not None:
            for f in fp.GetFields():
                if f.GetName() == name:
                    f.SetVisible(visible)

    # ------------------------------------------------------------ footprints (added/removed in save)
    def _part(self, ref, link, required):
        if not link:
            return None
        part = self._schematic(required=required).get(ref)
        if part is None and required:
            raise KeyError(f"{ref} isn't in the schematic; add it there first, or pass link=False")
        return part

    def _build(self, ref, footprint, value, fields, part, like=None):
        lib, _, name = (footprint or "").partition(":")
        if not name:
            raise ValueError(f'{ref}: footprint must be "Library:Footprint", e.g. "Resistor_SMD:R_0805_2012Metric"')
        lib_dir = kicadenv.footprint_lib_dir(lib, os.path.dirname(self.path))
        fp = pcbnew.FootprintLoad(lib_dir, name)
        if fp is None:
            raise KeyError(f"no footprint {name!r} in {lib_dir}")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(value if value is not None else (part["value"] if part else (like.GetValue() if like else name)))
        if part:
            fp.SetPath(pcbnew.KIID_PATH(part["path"]))
            fp.SetSheetname(part["sheetname"])
            fp.SetSheetfile(part["sheetfile"])
        elif like:
            fp.SetPath(like.GetPath())
            fp.SetSheetname(like.GetSheetname())
            fp.SetSheetfile(like.GetSheetfile())
        want = {}
        if like and not part:                     # no schematic entry: keep the old footprint's own fields,
            lib_fields = {f.GetName() for f in fp.GetFields()}   # but the new library's fields win
            want.update({f.GetName(): f.GetText() for f in like.GetFields()
                         if f.GetName() not in ("Reference", "Value", "Footprint") and f.GetName() not in lib_fields})
        if part:
            want.update(part["fields"])
            if part["dnp"] and hasattr(fp, "SetDNP"):
                fp.SetDNP(True)
            if part["exclude_from_bom"] and hasattr(fp, "SetExcludedFromBOM"):
                fp.SetExcludedFromBOM(True)
        want.update(fields or {})
        for k, v in want.items():
            fp.SetField(k, v)
        for f in fp.GetFields():
            if f.GetName() in want:
                f.SetVisible(False)
        if like:
            old, new = like.Reference(), fp.Reference()
            new.SetTextHeight(old.GetTextHeight()); new.SetTextWidth(old.GetTextWidth())
            new.SetTextThickness(old.GetTextThickness()); new.SetVisible(old.IsVisible())
        return fp

    def _stage(self, ref, fp, x, y, rot, side, nets, part, like):
        if side and (side == "B") != fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        old_nets = {p.GetNumber(): p.GetNetname() for p in like.Pads()} if (like and not part) else {}
        staged = []
        for p in fp.Pads():
            num = p.GetNumber()
            if part and num in part["pins"]:
                net = part["pins"][num]
                p.SetPinFunction(part["pinfunctions"].get(num, ""))
                if hasattr(p, "SetPinType"):
                    p.SetPinType(part["pintypes"].get(num, ""))
            else:
                net = old_nets.get(num, "")
            if nets and num in nets:
                net = nets[num] if nets[num] is not None else self._unconnected_name(ref, num)
            if net and net not in self.nets:
                self._pending_nets.add(net)
            staged.append((p, net))
        self.fps[ref] = fp
        self._added[ref] = fp
        self._added_pads[ref] = staged
        self._moved.append(ref)

    def add_footprint(self, ref, x, y, rot=0, side="F", footprint=None, value=None, fields=None, nets=None, link=True):
        """Add a part that's in the schematic but not on the board yet, at (x, y) mm, rot degrees.

        With link=True (the default) everything comes from the schematic next to the board: the footprint
        ("Library:Name" from the symbol's Footprint field), value, fields (LCSC, Description, ...), the symbol
        link KiCad's parity check needs, and each pad's net. footprint/value/fields/nets override it:
        nets maps pad number -> net name ("" = no net, None = KiCad's unconnected-(...) net).
        link=False adds an unlinked footprint (parity will report it as extra); then pass footprint= and nets=.
        """
        self._check()
        if ref in self.fps:
            raise ValueError(f"{ref} is already on the board; use replace_footprint")
        part = self._part(ref, link, required=True)
        fp = self._build(ref, footprint or (part["footprint"] if part else None), value, fields, part)
        self._stage(ref, fp, x, y, rot, side, nets, part, None)

    def replace_footprint(self, ref, footprint=None, x=None, y=None, rot=None, side=None, value=None, fields=None,
                          nets=None, link=True, tracks=True):
        """Swap a part's footprint (a new package, connector, or the schematic's newer pinout).

        Position, rotation, side and label size default to the old footprint's. With link=True the
        footprint, value, fields and pad nets come from the schematic (as add_footprint); without a
        schematic entry they're copied from the old footprint, nets matched by pad number. tracks=True
        also removes the copper attached to the old pads (see remove_footprint), since the new pads rarely
        land in the same places.
        """
        old = self._fp(ref)
        if ref in self._added:
            raise ValueError(f"{ref} is already new in this edit")
        part = self._part(ref, link, required=False)
        footprint = footprint or (part["footprint"] if part else old.GetFPIDAsString())
        fp = self._build(ref, footprint, value, fields, part, like=old)
        ox, oy, orot = self.position(ref)
        self._remove_staged(ref, old, tracks)
        self._stage(ref, fp, ox if x is None else x, oy if y is None else y, orot if rot is None else rot,
                    side or ("B" if old.IsFlipped() else "F"), nets, part, old)

    def _remove_staged(self, ref, fp, tracks):
        self._removed.append((ref, fp, tracks))
        del self.fps[ref]
        if ref in self._moved:
            self._moved.remove(ref)

    def remove_footprint(self, ref, tracks=True):
        """Remove a part from the board. tracks=True also removes the copper hanging off its pads: each track
        chain from a pad up to the next junction, via or other part's pad, and vias left with nothing
        else attached (e.g. a GND via on a stub). Longer routes beyond a junction stay; use remove_tracks."""
        fp = self._fp(ref)
        if ref in self._added:
            raise ValueError(f"{ref} was added in this edit; just don't add it")
        self._remove_staged(ref, fp, tracks)

    # ------------------------------------------------------------ board text
    def text(self, s, x, y, height=1.0, thickness=0.15, layer="F.SilkS", rot=0):
        """Free text on the board (a terminal's pin names, a version, a warning), centred on (x, y).
        1.0 / 0.15 mm is JLC's legibility minimum. Back-side text is mirrored, as KiCad does."""
        self._check()
        t = pcbnew.PCB_TEXT(self.board)
        lid = self._layer(layer)
        t.SetText(s)
        t.SetLayer(lid)
        t.SetTextHeight(MM(height)); t.SetTextWidth(MM(height)); t.SetTextThickness(MM(thickness))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetTextAngleDegrees(rot)
        if self.board.GetLayerName(lid).startswith("B."):
            t.SetMirrored(True)
        t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        self._texts.append(t)
        return t

    def _find_text(self, s, near):
        removed = {t.m_Uuid.AsString() for t in self._text_removes}
        hits = [d for d in self.board.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetText() == s
                and d.m_Uuid.AsString() not in removed]
        if not hits:
            raise KeyError(f"no board text {s!r}")
        def pos(d):
            return (round(TOMM(d.GetPosition().x), 2), round(TOMM(d.GetPosition().y), 2))
        if near is None:
            if len(hits) > 1:
                raise ValueError(f"{len(hits)} texts read {s!r}, at {[pos(d) for d in hits]}; pass near=(x, y)")
            return hits[0]
        return min(hits, key=lambda d: (pos(d)[0] - near[0]) ** 2 + (pos(d)[1] - near[1]) ** 2)

    def move_text(self, s, x, y, near=None):
        """Move existing board text that reads s (the one closest to near=(x, y) if several do). Immediate."""
        self._check()
        t = self._find_text(s, near)
        t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        self._text_moved.append(t)

    def remove_text(self, s, near=None):
        """Remove existing board text that reads s (the one closest to near=(x, y) if several do)."""
        self._check()
        self._text_removes.append(self._find_text(s, near))

    def remove_tracks(self, nets=None, layers=None, region=None, vias=True, tracks=True):
        """Remove existing tracks and/or vias matching every given filter.

        nets: list of net names; layers: list of layer names (tracks only); region: (x0, y0, x1, y1),
        matching items with both ends (or the via) inside. With no filter at all, nothing is removed:
        pass nets=["*"] to mean every net.
        """
        if not (nets or layers or region):
            raise ValueError("remove_tracks needs at least one filter; nets=['*'] matches every net")
        self._removes.append((nets, layers, region, vias, tracks))

    def label(self, ref, x=None, y=None, height=None, thickness=None):
        """Put a reference label at (x, y), horizontal. Without x and y it stays where it is, so
        label(ref, height=1.0, thickness=0.15) just resizes it."""
        self._fp(ref)
        if (x is None) != (y is None):
            raise ValueError("give both x and y, or neither")
        self._labels[ref] = (x, y, height, thickness)

    def auto_labels(self, refs=None, prefer=None, height=None, thickness=None):
        """Place references beside their parts, clear of pads, vias, silkscreen and other labels.

        refs defaults to every part moved with place(). prefer maps ref -> sides to try first, from
        "above", "below", "left", "right" (the four diagonals follow). height/thickness resize the
        labels (JLC's legibility minimum is 1.0 / 0.15 mm); None keeps the current size. A label that
        finds no clear spot keeps its old position (at the new size) and is reported by save().
        """
        self._auto = (refs, prefer or {}, height, thickness)

    # ------------------------------------------------------------ save
    def _check(self):
        if self._saved:
            raise RuntimeError("this Board was saved. Edit again from a new process: after an add or remove, "
                               "pcbnew objects break for the rest of the process, even for newly loaded boards")

    def _place_labels(self):
        b = self.board
        def bb(box, m=0.0):
            return (TOMM(box.GetLeft()) - m, TOMM(box.GetTop()) - m, TOMM(box.GetRight()) + m, TOMM(box.GetBottom()) + m)
        def hit(a, c):
            return a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]

        auto_refs = []
        if self._auto:
            refs, prefer, h, th = self._auto
            auto_refs = list(dict.fromkeys(refs if refs is not None else self._moved))
        movers = set(auto_refs) | set(self._labels)
        rects, polys = [], []
        for ref, fp in self.fps.items():
            for p in fp.Pads():
                rects.append(bb(p.GetBoundingBox(), 0.15))
            for g in fp.GraphicalItems():
                if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and g.GetClass() not in ("PCB_FIELD", "PCB_TEXT"):
                    ps = pcbnew.SHAPE_POLY_SET()
                    g.TransformShapeToPolygon(ps, g.GetLayer(), MM(0.1), MM(0.01), pcbnew.ERROR_OUTSIDE)
                    polys.extend(_poly_points(ps))
            if ref not in movers and fp.Reference().IsVisible():
                rects.append(bb(fp.Reference().GetBoundingBox(), 0.1))
        silk = (pcbnew.F_SilkS, pcbnew.B_SilkS)
        removed = {t.m_Uuid.AsString() for t in self._text_removes}
        for d in list(b.GetDrawings()) + self._texts:      # board-level silkscreen: free text and shapes
            if d.GetLayer() not in silk or d.m_Uuid.AsString() in removed:
                continue
            if d.GetClass() == "PCB_TEXT":
                rects.append(bb(d.GetBoundingBox(), 0.1))
            elif d.GetClass() == "PCB_SHAPE":
                ps = pcbnew.SHAPE_POLY_SET()
                d.TransformShapeToPolygon(ps, d.GetLayer(), MM(0.1), MM(0.01), pcbnew.ERROR_OUTSIDE)
                polys.extend(_poly_points(ps))
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                q, r = t.GetPosition(), TOMM(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.1
                rects.append((TOMM(q.x) - r, TOMM(q.y) - r, TOMM(q.x) + r, TOMM(q.y) + r))
        for (x, y, net, d, h) in self._vias:
            rects.append((x - d / 2 - 0.1, y - d / 2 - 0.1, x + d / 2 + 0.1, y + d / 2 + 0.1))
        el, et, er, eb = bb(b.GetBoardEdgesBoundingBox())
        edge = (el + 0.6, et + 0.6, er - 0.6, eb - 0.6)

        def blocked(box):
            if box[0] < edge[0] or box[1] < edge[1] or box[2] > edge[2] or box[3] > edge[3]:
                return True
            return any(hit(box, o) for o in rects) or any(_rect_hits_poly(box, p) for p in polys)

        def size(t, h, th):
            t.SetTextAngleDegrees(0)
            t.SetKeepUpright(True)
            if h:
                t.SetTextHeight(MM(h)); t.SetTextWidth(MM(h))
            if th:
                t.SetTextThickness(MM(th))

        for ref, (x, y, h, th) in self._labels.items():
            t = self.fps[ref].Reference()
            keep = t.GetPosition()
            size(t, h, th)
            t.SetPosition(keep if x is None else pcbnew.VECTOR2I(MM(x), MM(y)))
            rects.append(bb(t.GetBoundingBox()))

        unplaced = []
        if self._auto:
            refs, prefer, h, th = self._auto
            order = sorted((r for r in auto_refs if r not in self._labels), key=lambda r: self.position(r)[:2])
            unit = {"right": (1, 0), "left": (-1, 0), "above": (0, -1), "below": (0, 1),
                    "ur": (0.7, -0.7), "ul": (-0.7, -0.7), "lr": (0.7, 0.7), "ll": (-0.7, 0.7)}
            for ref in order:
                fp = self.fps[ref]
                t = fp.Reference()
                old = t.GetPosition()
                size(t, h, th)
                cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
                l, tp, r, bt = bb(cy.BBox()) if cy.OutlineCount() else bb(fp.GetBoundingBox(False))
                cx, cyy = (l + r) / 2, (tp + bt) / 2
                t.SetPosition(pcbnew.VECTOR2I(MM(cx), MM(cyy)))
                w, hh = TOMM(t.GetBoundingBox().GetWidth()), TOMM(t.GetBoundingBox().GetHeight())
                base = {"above": (cx, tp - hh / 2 + 0.05), "below": (cx, bt + hh / 2 - 0.05),
                        "right": (r + w / 2 - 0.05, cyy), "left": (l - w / 2 + 0.05, cyy),
                        "ur": (r + w / 2 - 0.4, tp - hh / 2 + 0.3), "ul": (l - w / 2 + 0.4, tp - hh / 2 + 0.3),
                        "lr": (r + w / 2 - 0.4, bt + hh / 2 - 0.3), "ll": (l - w / 2 + 0.4, bt + hh / 2 - 0.3)}
                pref = ["right", "left", "above", "below"] if (bt - tp) > (r - l) else ["above", "below", "right", "left"]
                pref = list(dict.fromkeys(list(prefer.get(ref, [])) + pref + ["ur", "ul", "lr", "ll"]))
                chosen = None
                for step in (0.0, 0.3, 0.6, 0.9, 1.2, 1.6, 2.0):
                    for side in pref:
                        x, y = base[side][0] + unit[side][0] * step, base[side][1] + unit[side][1] * step
                        box = (x - w / 2, y - hh / 2, x + w / 2, y + hh / 2)
                        if not blocked(box):
                            chosen = (x, y, box)
                            break
                    if chosen:
                        break
                if chosen:
                    t.SetPosition(pcbnew.VECTOR2I(MM(chosen[0]), MM(chosen[1])))
                    rects.append(chosen[2])
                else:
                    t.SetPosition(old)
                    unplaced.append(ref)
        return unplaced

    def _select_removals(self):
        out = []
        for t in self.board.GetTracks():
            is_via = t.GetClass() == "PCB_VIA"
            for nets, layers, region, vias, tracks in self._removes:
                if (is_via and not vias) or (not is_via and not tracks):
                    continue
                if nets and "*" not in nets and t.GetNetname() not in nets:
                    continue
                if layers and (is_via or self.board.GetLayerName(t.GetLayer()) not in layers):
                    continue
                if region:
                    x0, y0, x1, y1 = region
                    pts = [t.GetPosition()] if is_via else [t.GetStart(), t.GetEnd()]
                    if not all(x0 <= TOMM(p.x) <= x1 and y0 <= TOMM(p.y) <= y1 for p in pts):
                        continue
                out.append(t)
                break
        return out

    def _attached_tracks(self):
        """Tracks and vias hanging off the pads of footprints being removed (read phase)."""
        follow = [fp for _, fp, tracks in self._removed if tracks]
        if not follow:
            return []
        items = list(self.board.GetTracks())
        segs = [t for t in items if t.GetClass() in ("PCB_TRACK", "PCB_ARC")]
        vias = [t for t in items if t.GetClass() == "PCB_VIA"]
        uid = lambda t: t.m_Uuid.AsString()
        ends = {}
        for s in segs:
            for p in (s.GetStart(), s.GetEnd()):
                ends.setdefault((p.x, p.y, s.GetLayer()), []).append(s)
        gone = {id(fp) for fp in follow}
        other_pads = [p for fp in self._loaded.values() if id(fp) not in gone for p in fp.Pads()]

        def via_at(p):
            for v in vias:
                q = v.GetPosition()
                if (q.x - p.x) ** 2 + (q.y - p.y) ** 2 <= (v.GetWidth(pcbnew.F_Cu) / 2) ** 2:
                    return v
            return None

        out, cand = {}, []
        for fp in follow:
            for pad in fp.Pads():
                for s in segs:
                    if uid(s) in out or not pad.IsOnLayer(s.GetLayer()):
                        continue
                    for came in (s.GetStart(), s.GetEnd()):
                        if not pad.HitTest(came):
                            continue
                        stack = [(s, came)]
                        while stack:
                            cur, at = stack.pop()
                            if uid(cur) in out:
                                continue
                            out[uid(cur)] = cur
                            a, c = cur.GetStart(), cur.GetEnd()
                            far = c if (a.x, a.y) == (at.x, at.y) else a
                            layer = cur.GetLayer()
                            v = via_at(far)
                            if v is not None:
                                cand.append(v)
                                continue
                            if any(p.IsOnLayer(layer) and p.HitTest(far) for p in other_pads):
                                continue
                            nxt = [o for o in ends.get((far.x, far.y, layer), []) if uid(o) != uid(cur)]
                            if len(nxt) == 1:
                                stack.append((nxt[0], far))
                        break
        for v in cand:
            q, r2 = v.GetPosition(), (v.GetWidth(pcbnew.F_Cu) / 2) ** 2
            touching = [s for s in segs if any((p.x - q.x) ** 2 + (p.y - q.y) ** 2 <= r2 for p in (s.GetStart(), s.GetEnd()))]
            if all(uid(s) in out for s in touching):
                out[uid(v)] = v
        return list(out.values())

    def save(self, path=None, refill_zones=True):
        """Apply queued edits and write the board (default: over the file it was loaded from).

        Returns a dict: tracks/vias added and removed, nets changed, footprints and texts added/removed,
        and labels that found no spot.
        """
        self._check()
        b = self.board
        unplaced = self._place_labels()            # reads first
        removals = self._select_removals()
        seen = {t.m_Uuid.AsString() for t in removals}
        removals += [t for t in self._attached_tracks() if t.m_Uuid.AsString() not in seen]
        pads = {(ref, num): self._pad(ref, num) for ref, num, _ in self._net_changes}
        names = {(ref, num): self._pad(ref, num).GetPinFunction() for ref, num, _ in self._net_changes}

        for net in sorted(self._pending_nets):     # then mutations
            if net not in self.nets:
                item = pcbnew.NETINFO_ITEM(b, net)
                b.Add(item)
                self.nets[net] = item
        for ref, num, net in self._net_changes:
            if net is None:
                net = self._unconnected_name(ref, num, names[(ref, num)])
            if net not in self.nets:
                item = pcbnew.NETINFO_ITEM(b, net)
                b.Add(item)
                self.nets[net] = item
            pads[(ref, num)].SetNet(self.nets[net])
        for ref, staged in self._added_pads.items():
            for pad, net in staged:
                if net:
                    pad.SetNet(self.nets[net])
        for t in removals:
            b.Remove(t)
        for _, fp, _ in self._removed:
            b.Remove(fp)
        for fp in self._added.values():
            b.Add(fp)
        for t in self._text_removes:
            b.Remove(t)
        for t in self._texts:
            b.Add(t)
        for (x, y, net, d, h) in self._vias:
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            v.SetWidth(MM(d))
            v.SetDrill(MM(h))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(self.nets[net])
            b.Add(v)
        for net, pts, w, layer in self._tracks:
            for a, c in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
                t.SetEnd(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
                t.SetWidth(MM(w))
                t.SetLayer(layer)
                t.SetNet(self.nets[net])
                b.Add(t)
        out = path or self.path
        b.Save(out)
        self._saved = True
        if refill_zones:
            r = subprocess.run([kicadenv.kicad_cli(), "pcb", "drc", "--refill-zones", "--save-board",
                                "-o", os.devnull, out], capture_output=True, text=True)
            if r.returncode not in (0, 5):
                print(f"zone refill failed ({r.returncode}): {r.stderr.strip()}", file=sys.stderr)
        result = {"tracks_added": sum(len(p) - 1 for _, p, _, _ in self._tracks), "vias_added": len(self._vias),
                  "removed": len(removals), "nets_changed": len(self._net_changes),
                  "footprints_added": sorted(r for r in self._added if r not in {x for x, _, _ in self._removed}),
                  "footprints_replaced": sorted(r for r, _, _ in self._removed if r in self._added),
                  "footprints_removed": sorted(r for r, _, _ in self._removed if r not in self._added),
                  "texts_added": len(self._texts), "texts_moved": len(self._text_moved),
                  "texts_removed": len(self._text_removes), "unplaced_labels": unplaced}
        if unplaced:
            print(f"no clear label spot for {', '.join(unplaced)}; place them with label()", file=sys.stderr)
        return result
