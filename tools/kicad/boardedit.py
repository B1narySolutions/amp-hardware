"""Incremental, scripted edits to a KiCad board. Import it from a script run under KiCad's Python.

    import sys; sys.path.insert(0, "tools/kicad")
    from boardedit import Board

    b = Board("audio-board/rev2/seed3-carrier.kicad_pcb")
    b.place("R1", 127.86, 85.4, rot=90)                  # mm, degrees; immediate
    b.track("/VREF", [b.pad("R6", "2"), b.pad("R1", "2")], width=0.25)
    b.via(124.6, 87.75, "GND")
    b.gnd_via("C7", "1", dx=0, dy=1.6)                   # via plus a short stub from the pad
    b.set_pad_net("A1", "23", "/HP_DETECT")              # None leaves the pad unconnected
    b.remove_tracks(nets=["/VREF"])                      # removes only what the filter names
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
        fixed = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu}
        if name in fixed:
            return fixed[name]
        lid = self.board.GetLayerID(name)
        if lid < 0:
            raise KeyError(f"no layer {name!r}")
        return lid

    def _net(self, name):
        if name not in self.nets:
            raise KeyError(f"no net {name!r} on the board (nets come from pads, tracks and zones that use them)")
        return self.nets[name]

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
        self._net_changes.append((ref, str(num), net))

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

    def save(self, path=None, refill_zones=True):
        """Apply queued edits and write the board (default: over the file it was loaded from).

        Returns a dict: tracks/vias added and removed, nets changed, and labels that found no spot.
        """
        self._check()
        b = self.board
        unplaced = self._place_labels()            # reads first
        removals = self._select_removals()
        pads = {(ref, num): self._pad(ref, num) for ref, num, _ in self._net_changes}
        names = {(ref, num): (self.fps[ref].GetReference(), self._pad(ref, num).GetPinFunction()) for ref, num, _ in self._net_changes}

        for ref, num, net in self._net_changes:    # then mutations
            if net is None:
                r, pin = names[(ref, num)]
                if pin.endswith("_" + num):          # pin functions carry a _<number> suffix KiCad drops here
                    pin = pin[: -len(num) - 1]
                net = f"unconnected-({r}-{pin or num}-Pad{num})"
            if net not in self.nets:
                item = pcbnew.NETINFO_ITEM(b, net)
                b.Add(item)
                self.nets[net] = item
            pads[(ref, num)].SetNet(self.nets[net])
        for t in removals:
            b.Remove(t)
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
                  "removed": len(removals), "nets_changed": len(self._net_changes), "unplaced_labels": unplaced}
        if unplaced:
            print(f"no clear label spot for {', '.join(unplaced)}; place them with label()", file=sys.stderr)
        return result
