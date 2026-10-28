"""Worst-case bounds on the voltages and currents in a circuit, for one case of a spec, without running a simulator.
circuit_verify.py builds the circuit from the schematic and part models, and turns these bounds into checks.

How a bound is computed
-----------------------
A case becomes a linear circuit: resistors, capacitors, amplifiers as voltage-controlled sources, and the rails, ports
and model outputs as sources. Any quantity (a pin's voltage, a resistor's current) is a sum over the sources:

  dc source    constant, somewhere in lo..hi      DC gain × lo..hi
  wave source  any waveform inside lo..hi         DC gain × mid  ±  ∫|h(t)| dt × half-range
  tone source  a sine of any frequency in a band  DC gain × offset  ±  max |H(jω)| in the band × peak

h is the impulse response from the source to the quantity, H its frequency response. The wave line is the exact
worst case for a linear circuit: no waveform inside the range drives the output further, and some waveform gets
arbitrarily close. It is why a coupling cap into a resistor can swing twice its input range, which a sine sweep
never shows.

Tolerances. DC gains are evaluated at every corner of the resistor tolerances (up to 2^14 corners). That is exact for
networks of resistors and followers: each node voltage is monotonic in each resistor. The dynamic terms use every
corner of the resistor and capacitor tolerances when there are at most 10, and otherwise nominal, the two extremes and
256 sampled corners. The worst DC corner and the worst dynamic corner are added even if they are different corners,
which can only overstate a bound.

Nonlinear parts. A clamp (an ESD diode, an IC's protection diodes, an amplifier's output reaching its rail) that can
conduct pins its node inside its window. That node is replaced by a source that can be any waveform in its narrower
range. That is sound for every other node, but a bound that goes through it is marked loose: it may be far above what
can really happen (a clipped sine is not a square wave).
A clamp's current is bounded with its node held at the clamp voltage and the other diode clamps off. Those clamps draw
current away from the circuit when they conduct, so leaving them out mostly overstates the current. Keeping them as
independent sources would overstate it far more.
MOSFETs are switches whose state follows the bounds on their gate drive. When a gate can sit on either side of its
threshold, both states are analysed.
"""
import itertools
import math
import random

from collections import namedtuple

import numpy as np

from circuit_spec import Stim, dc

# lo..hi bounds a quantity. kind is "dc" when only constant sources reach it. loose means the bound goes through a node
# a clamp holds (treated as any waveform inside the clamp's window), so it may be far from what can really happen;
# otherwise the bound is tight: some source waveform and part tolerances reach it, or come arbitrarily close.
Bound = namedtuple("Bound", "lo hi kind loose")

GMIN = 1e-12          # S from every node to GND, as SPICE does, so a node held only by caps still has a DC solution
ESR = 1e-3            # Ω in series with a cap that would otherwise close a loop of caps and sources
EXACT_DC = 14         # resistor tolerances enumerated exactly up to this many
EXACT_DYN = 10        # resistor + capacitor tolerances enumerated exactly up to this many
SAMPLED = 256
PER_DECADE = 40


class Elem:
    """A circuit element.

    R  resistor (a, b)                      value Ω
    C  capacitor (a, b)                     value F
    E  voltage-controlled source (out, in+, in−): V(out) = gain × (V(in+) − V(in−))
    D  clamp (a, b): conducts from a to b once V(a) − V(b) exceeds v_on, which spans vmin..vmax
    S  switch (d, s, g): a MOSFET channel, on (r_on) or off by its gate drive polarity × (V(g) − V(s)) against vth
    """

    def __init__(self, kind, name, nodes, value=0.0, tol=0.0, owner=None, **kw):
        self.kind, self.name, self.nodes, self.value, self.tol, self.owner = kind, name, tuple(nodes), value, tol, owner
        self.__dict__.update(kw)

    def key(self):
        return (self.kind, self.name, self.nodes, self.value, self.tol)

    def __repr__(self):
        return f"<{self.kind} {self.name} {self.nodes}>"


class Circuit:
    """One case's circuit: elements, fixed nodes (sources) and everything the checks need to know about the parts."""

    def __init__(self, gnd):
        self.gnd = gnd
        self.elems = []
        self.fixed = {}       # node -> Stim
        self.fixed_by = {}    # node -> what drives it
        self.limits, self.loads, self.drives, self.notes = [], [], [], []

    def add(self, elem):
        if any(e.name == elem.name for e in self.elems):
            raise ValueError(f"two elements are named {elem.name}")
        self.elems.append(elem)
        return elem

    def fix(self, node, stim, what):
        if node == self.gnd:
            raise ValueError(f"{what} drives GND")
        if node in self.fixed:
            raise ValueError(f"{node} is driven by both {self.fixed_by[node]} and {what}")
        self.fixed[node], self.fixed_by[node] = stim, what

    def level(self, v):
        """A fixed node at a constant voltage, for clamps to a level rather than a net."""
        name = f"level:{v:g}"
        if name not in self.fixed:
            self.fix(name, dc(v), "clamp level")
        return name

    def element(self, name):
        for e in self.elems:
            if e.name == name:
                return e
        raise KeyError(name)


# ------------------------------------------------------------------------------------------------------- linear groups


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def _corners(elems, exact, sampled, seed):
    """Part values at tolerance corners. Returns (list of {name: value}, exhaustive?)."""
    def at(bits):
        return {e.name: e.value * (1 + e.tol if b else 1 - e.tol) for e, b in zip(elems, bits)}
    if len(elems) <= exact:
        return [at(bits) for bits in itertools.product((0, 1), repeat=len(elems))], True
    rng = random.Random(seed)
    out = [{e.name: e.value for e in elems}, at([0] * len(elems)), at([1] * len(elems))]
    out += [at([rng.randint(0, 1) for _ in elems]) for _ in range(sampled)]
    return out, False


class Group:
    """A linear subcircuit: non-fixed nodes, the elements between them, and the fixed nodes that drive them.

    Holds the DC gains at every resistor corner and the state-space modes at every dynamic corner, so any number of
    quantities and source combinations can be bounded without solving again.
    """

    def __init__(self, nodes, fixed, elems, gnd, probes=()):
        self.gnd = gnd
        self.fixed = sorted(fixed)
        self.probes = list(probes)
        self.res = [e for e in elems if e.kind in "RS"]
        self.vcvs = [e for e in elems if e.kind == "E"]
        self.by_name = {e.name: e for e in elems}

        # Parallel caps share one state. A cap that closes a loop of caps, sources and amplifier outputs gets a small
        # series resistance so that every cap voltage can be a state.
        pairs = {}
        for e in elems:
            if e.kind == "C" and e.nodes[0] != e.nodes[1]:
                pairs.setdefault(tuple(sorted(e.nodes)), []).append(e)
        uf, ground = _UF(), "\0ground"
        for f in self.fixed + [gnd]:
            uf.union(f, ground)
        for e in self.vcvs:
            uf.union(e.nodes[0], ground)
        self.caps, self.esr, extra = [], [], []
        for (a, b), cs in sorted(pairs.items()):
            if uf.find(a) == uf.find(b):
                mid = f"esr:{cs[0].name}"
                extra.append(mid)
                self.esr.append((a, mid))
                a = mid
            else:
                uf.union(a, b)
            self.caps.append((a, b, cs))
        self.nodes = sorted(nodes) + extra
        self.all_nodes = self.nodes + self.fixed
        self.idx = {n: i for i, n in enumerate(self.all_nodes)}
        self.inputs = self.fixed + [f"probe:{p}" for p in self.probes]
        self.tol_r = [e for e in elems if e.kind == "R" and e.tol > 0]
        self.tol_all = self.tol_r + [e for e in elems if e.kind == "C" and e.tol > 0]
        self._dc = self._dyn = None
        self.exhaustive = True

    # -- matrices

    def _matrices(self, vals, with_caps):
        nn, F, P = len(self.all_nodes), len(self.fixed), len(self.probes)
        NC = len(self.caps) if with_caps else 0
        NE = len(self.vcvs)
        size = nn + F + NC + NE
        M = np.zeros((size, size))
        N = np.zeros((size, F + P + NC))
        idx = self.idx

        def g(a, b, cond):
            ia, ib = idx.get(a), idx.get(b)
            if ia is not None:
                M[ia, ia] += cond
            if ib is not None:
                M[ib, ib] += cond
            if ia is not None and ib is not None:
                M[ia, ib] -= cond
                M[ib, ia] -= cond

        for e in self.res:
            g(e.nodes[0], e.nodes[1], 1.0 / vals.get(e.name, e.value))
        for a, mid in self.esr:
            g(a, mid, 1.0 / ESR)
        for n in self.nodes:
            M[idx[n], idx[n]] += GMIN
        for k, f in enumerate(self.fixed):
            row = nn + k
            M[idx[f], row] += 1
            M[row, idx[f]] += 1
            N[row, k] = 1
        for k in range(NC):
            a, b, _ = self.caps[k]
            row = nn + F + k
            if a in idx:
                M[idx[a], row] += 1
                M[row, idx[a]] += 1
            if b in idx:
                M[idx[b], row] -= 1
                M[row, idx[b]] -= 1
            N[row, F + P + k] = 1
        for k, e in enumerate(self.vcvs):
            row = nn + F + NC + k
            out, inp, inn = e.nodes
            M[idx[out], row] += 1
            M[row, idx[out]] += 1.0 / e.value if e.value else 1.0
            if e.value:
                if inp in idx:
                    M[row, idx[inp]] -= 1
                if inn in idx:
                    M[row, idx[inn]] += 1
        for k, p in enumerate(self.probes):
            N[idx[p], F + k] = 1
        return M, N

    def _weights(self, terms, vals):
        w = np.zeros(len(self.all_nodes) + len(self.fixed))
        nn = len(self.all_nodes)
        for kind, what, k in terms:
            if kind == "v":
                if what != self.gnd:
                    w[self.idx[what]] += k
            elif kind == "i":
                w[nn + self.fixed.index(what)] += k
            elif kind == "r":
                e = self.by_name[what]
                cond = k / vals.get(e.name, e.value)
                a, b = e.nodes[0], e.nodes[1]
                if a != self.gnd:
                    w[self.idx[a]] += cond
                if b != self.gnd:
                    w[self.idx[b]] -= cond
        return w

    # -- DC: every resistor corner

    def _dc_data(self):
        if self._dc is None:
            corners, exact = _corners(self.tol_r, EXACT_DC, 4096, seed=1)
            self.exhaustive &= exact
            data = []
            for vals in corners:
                M, N = self._matrices(vals, with_caps=False)
                Z = np.linalg.solve(M, N)
                data.append((vals, Z[: len(self.all_nodes) + len(self.fixed)]))
            self._dc = data
        return self._dc

    def dc_gains(self, targets):
        """corners × targets × inputs DC gains."""
        out = []
        for vals, Z in self._dc_data():
            W = np.array([self._weights(t, vals) for t in targets])
            out.append(W @ Z)
        return np.array(out)

    # -- dynamics: state-space modes at each dynamic corner

    def _dyn_data(self):
        if self._dyn is None:
            corners, exact = _corners(self.tol_all, EXACT_DYN, SAMPLED, seed=2)
            self.exhaustive &= exact
            data = []
            nn, F, P = len(self.all_nodes), len(self.fixed), len(self.probes)
            for vals in corners:
                if not self.caps:
                    M, N = self._matrices(vals, with_caps=False)
                    Z = np.linalg.solve(M, N)
                    data.append((vals, None, None, None, Z[: nn + F, : F + P]))
                    continue
                M, N = self._matrices(vals, with_caps=True)
                Z = np.linalg.solve(M, N)
                NC = len(self.caps)
                cvals = np.array([sum(vals.get(c.name, c.value) for c in cs) for _, _, cs in self.caps])
                rows = slice(nn + F, nn + F + NC)
                xcols = slice(F + P, F + P + NC)
                A = Z[rows, xcols] / cvals[:, None]
                B = Z[rows, : F + P] / cvals[:, None]
                Cz = Z[: nn + F, xcols]
                Dz = Z[: nn + F, : F + P]
                lam, Vm = np.linalg.eig(A)
                if np.linalg.cond(Vm) > 1e10:
                    # Repeated modes (identical RC sections): separate them slightly so the matrix diagonalises.
                    A = A * (1 + 1e-7 * np.arange(1, NC + 1))[:, None]
                    lam, Vm = np.linalg.eig(A)
                if np.max(lam.real) > 1e-9 * max(1.0, np.max(np.abs(lam))):
                    raise RuntimeError("a linear group is unstable (positive feedback?): " + ", ".join(self.nodes[:6]))
                Vinv = np.linalg.inv(Vm)
                data.append((vals, lam, Cz @ Vm, Vinv @ B, Dz))
            self._dyn = data
        return self._dyn

    def _modal(self, targets):
        """For each dynamic corner: (lam, a = targets × modes, b = modes × inputs, d = targets × inputs)."""
        out = []
        for vals, lam, CzV, VinvB, Dz in self._dyn_data():
            W = np.array([self._weights(t, vals) for t in targets])
            d = W @ Dz
            if lam is None:
                out.append((None, None, None, d))
            else:
                out.append((lam, W @ CzV, VinvB, d))
        return out

    def l1(self, targets):
        """corners × targets × inputs: ∫|h(t)| dt, the worst-case peak gain for any bounded waveform."""
        res = []
        for lam, a, b, d in self._modal(targets):
            if lam is None:
                res.append(np.abs(d))
                continue
            rate = -lam.real
            fast, slow = max(np.max(np.abs(lam)), 1e-30), max(np.min(rate), 1e-12)
            t0, t1 = 1e-3 / fast, 40.0 / slow
            t = np.geomspace(t0, t1, max(int(PER_DECADE * math.log10(t1 / t0)), 50))
            E = np.exp(np.outer(lam, t))
            h = np.real(np.einsum("tk,kj,kg->tjg", a, b, E))
            f = np.abs(h) * t
            lt = np.log(t)
            integral = np.sum((f[:, :, 1:] + f[:, :, :-1]) * 0.5 * np.diff(lt), axis=2) + np.abs(h[:, :, 0]) * t0
            res.append(np.abs(d) + integral)
        return np.array(res)

    def _freqs(self, band, lams):
        f1, f2 = band
        f = np.geomspace(f1, f2, max(int(PER_DECADE * math.log10(f2 / f1)) + 1, 2))
        res = [abs(x.imag) / (2 * math.pi) for lam in lams if lam is not None for x in lam]
        f = np.concatenate([f, [x for x in res if f1 < x < f2]])
        return 2 * math.pi * f

    def h_band(self, targets, band):
        """corners × targets × inputs: max |H(jω)| over the band, the peak gain for a sine anywhere in it."""
        res = []
        for lam, a, b, d in self._modal(targets):
            if lam is None:
                res.append(np.abs(d))
                continue
            w = self._freqs(band, [lam])
            R = 1.0 / (1j * w[None, :] - lam[:, None])
            H = d[:, :, None] + np.einsum("tk,kj,kf->tjf", a, b, R)
            res.append(np.max(np.abs(H), axis=2))
        return np.array(res)

    def h_at(self, targets, f):
        """corners × targets × inputs: H(j2πf)."""
        res = []
        w = 2 * math.pi * f
        for lam, a, b, d in self._modal(targets):
            if lam is None:
                res.append(d.astype(complex))
                continue
            R = 1.0 / (1j * w - lam)
            res.append(d + np.einsum("tk,kj,k->tj", a, b, R))
        return np.array(res)

    def h_band_min(self, targets, band):
        """corners × targets × inputs: min |H(jω)| over the band (an impedance's lowest point)."""
        res = []
        for lam, a, b, d in self._modal(targets):
            if lam is None:
                res.append(np.abs(d))
                continue
            w = self._freqs(band, [lam])
            R = 1.0 / (1j * w[None, :] - lam[:, None])
            H = d[:, :, None] + np.einsum("tk,kj,kf->tjf", a, b, R)
            res.append(np.min(np.abs(H), axis=2))
        return np.array(res)

    def bounds(self, targets, stims, subs=frozenset()):
        """A Bound for each target, given the Stim on each fixed node. subs are the fixed nodes that stand in for
        clamped nodes: a target they reach is loose."""
        J = len(self.fixed)
        G = self.dc_gains(targets)[:, :, :J]                       # corners × T × J
        lo = np.zeros(G.shape[:2])
        hi = np.zeros(G.shape[:2])
        dyn_inputs = {}
        for j, f in enumerate(self.fixed):
            s = stims[f]
            if s.kind == "dc":
                a, b = G[:, :, j] * s.lo, G[:, :, j] * s.hi
                lo += np.minimum(a, b)
                hi += np.maximum(a, b)
            else:
                lo += G[:, :, j] * s.mid
                hi += G[:, :, j] * s.mid
                if s.amp > 0:
                    dyn_inputs[j] = s
        dyn = np.zeros(len(targets))
        reach = np.abs(G).max(axis=0) > 1e-12                       # T × J: which inputs reach which target
        if dyn_inputs:
            total = None
            waves = [j for j, s in dyn_inputs.items() if s.kind == "wave"]
            if waves:
                L = self.l1(targets)
                part = sum(L[:, :, j] * dyn_inputs[j].amp for j in waves)
                total = part if total is None else total + part
                reach[:, waves] |= L[:, :, waves].max(axis=0) > 1e-12
            for band in {s.band for s in dyn_inputs.values() if s.kind == "tone"}:
                tones = [j for j, s in dyn_inputs.items() if s.kind == "tone" and s.band == band]
                Hb = self.h_band(targets, band)
                part = sum(Hb[:, :, j] * dyn_inputs[j].amp for j in tones)
                total = part if total is None else total + part
                reach[:, tones] |= Hb[:, :, tones].max(axis=0) > 1e-12
            dyn = np.max(total, axis=0)
        nondc = [j for j, f in enumerate(self.fixed) if stims[f].kind != "dc"]
        sub = [j for j, f in enumerate(self.fixed) if f in subs]
        out = []
        for t in range(len(targets)):
            kind = "wave" if nondc and reach[t, nondc].any() else "dc"
            loose = bool(sub) and bool(reach[t, sub].any())
            out.append(Bound(float(np.min(lo[:, t]) - dyn[t]), float(np.max(hi[:, t]) + dyn[t]), kind, loose))
        return out


def _bang_bang(lam, a, b, d, j, st, side, max_edges=400):
    """The input inside st's range that drives the output furthest at time T: u(T − τ) = mid ± amp × sign(h(τ)).
    Returns PWL points; the output reaches the L1 bound at the last one."""
    if lam is None:
        level = st.mid + st.amp * (1 if side * d[0, j].real > 0 else -1)
        return [(0.0, level), (1e-6, level)]
    rate = -lam.real
    t0, t1 = 1e-3 / max(np.max(np.abs(lam)), 1e-30), 40.0 / max(np.min(rate), 1e-12)
    tau = np.geomspace(t0, t1, max(int(PER_DECADE * 4 * math.log10(t1 / t0)), 200))
    h = np.real(np.einsum("k,k,kg->g", a[0], b[:, j], np.exp(np.outer(lam, tau))))
    # The horizon: where 99.9 % of ∫|h| has arrived.
    f = np.abs(h) * tau
    cum = np.concatenate([[0.0], np.cumsum((f[1:] + f[:-1]) * 0.5 * np.diff(np.log(tau)))])
    T = float(tau[min(int(np.searchsorted(cum, 0.999 * cum[-1])) + 1, len(tau) - 1)]) if cum[-1] > 0 else t0
    keep = tau <= T
    tau, h = tau[keep], h[keep]
    first = d[0, j].real if abs(d[0, j]) > 1e-12 else (h[0] if len(h) else 1.0)
    sign = np.sign(np.concatenate([[first], h]))
    sign[sign == 0] = 1
    taus = np.concatenate([[0.0], tau])
    level = lambda s: st.mid + st.amp * side * s
    # Walk from the oldest input (τ = T, t = 0) to the newest (τ = 0, t = T).
    pts, cur = [(0.0, level(sign[-1]))], sign[-1]
    edge = max(T * 1e-9, 1e-12)
    for k in range(len(taus) - 2, -1, -1):
        if sign[k] != cur:
            t = T - taus[k + 1]
            pts += [(t, level(cur)), (t + edge, level(sign[k]))]
            cur = sign[k]
    pts.append((T, level(cur)))
    if len(pts) > 2 * max_edges:
        pts = pts[:1] + pts[-2 * max_edges:]
    return pts


# ---------------------------------------------------------------------------------------------------------- analysis


class Analysis:
    """Bounds for one case. Call run(), then bound()/gain()/impedance() for anything else the checks need."""

    def __init__(self, circ, cache):
        self.circ, self.cache = circ, cache
        self.gnd = circ.gnd
        self.switches = [e for e in circ.elems if e.kind == "S"]
        self.clamps = [e for e in circ.elems if e.kind == "D"]
        self.nodes = sorted({n for e in circ.elems for n in e.nodes} - {self.gnd})
        self.sampled = False

    # -- structure

    def _active(self, fixed, sw, exclude=()):
        out = []
        for e in self.circ.elems:
            if e.name in exclude:
                continue
            if e.kind == "R":
                out.append(e)
            elif e.kind == "C":
                if not all(n in fixed or n == self.gnd for n in e.nodes):
                    out.append(e)
            elif e.kind == "E":
                if e.nodes[0] not in fixed:
                    out.append(e)
            elif e.kind == "S" and sw.get(e.name) == "on":
                out.append(Elem("S", e.name, e.nodes[:2], e.r_on))
        return out

    def _group(self, nodes, fixed, sw, extra_fixed=(), exclude=(), probes=()):
        active = self._active(fixed, sw, exclude)
        uf = _UF()
        free = lambda n: n != self.gnd and n not in fixed
        for e in active:
            ns = [n for n in e.nodes if free(n)]
            for n in ns:
                uf.find(n)
            for a, b in zip(ns, ns[1:]):
                uf.union(a, b)
        roots = {uf.find(n) for n in nodes if free(n)}
        members = {n for n in uf.p if uf.find(n) in roots}
        elems = [e for e in active if any(n in members for n in e.nodes)]
        adj = {n for e in elems for n in e.nodes if n in fixed}
        fx = sorted(adj | {n for n in extra_fixed if n in fixed})
        key = (tuple(sorted(members)), tuple(fx), tuple(sorted(e.key() for e in elems)), tuple(probes))
        g = self.cache.get(key)
        if g is None:
            g = self.cache[key] = Group(members, fx, elems, self.gnd, probes)
        return g

    # -- bounds

    def _fx(self, n, fixed):
        return n == self.gnd or n in fixed

    def bound(self, terms_list, fixed=None, sw=None, pinned=()):
        """A Bound for each target. A target is a list of terms ("v", node, k), ("r", resistor, k) or ("i", fixed
        node, k): node voltages, resistor currents (pin 1 → 2) and currents from the circuit into a source. Nodes in
        `fixed` that the circuit doesn't fix itself are clamp substitutions, except the `pinned` ones."""
        fixed = self.fixed if fixed is None else fixed
        sw = self.sw if sw is None else sw
        subs = frozenset(n for n in fixed if n not in self.circ.fixed and n not in pinned)
        active = self._active(fixed, sw)
        terms_list = [self._merge(t) for t in terms_list]
        out = [None] * len(terms_list)
        groups = {}
        for t, terms in enumerate(terms_list):
            # A current into a source sums over every element on it: the ones between two fixed nodes are worked out
            # directly, the rest through the linear group(s) beside it.
            direct = [(k_, w, k) for k_, w, k in terms if k_ != "i"]
            extra = Bound(0.0, 0.0, "dc", False)
            for k_, f, k in terms:
                if k_ == "i":
                    for e in active:
                        if e.kind == "R" and f in e.nodes and all(self._fx(n, fixed) for n in e.nodes):
                            extra = self._add(extra, self._r_direct(e, k if e.nodes[1] == f else -k, fixed, subs))
            nodes = set(self._term_nodes(terms, active, fixed))
            free = [n for n in nodes if not self._fx(n, fixed)]
            if not free:
                out[t] = self._add(self._direct(direct, fixed, subs), extra)
                continue
            g = self._group(free, fixed, sw, extra_fixed=[n for n in nodes if n in fixed])
            groups.setdefault(id(g), (g, []))[1].append((t, extra))
        for g, ts in groups.values():
            res = g.bounds([terms_list[t] for t, _ in ts], fixed, subs)
            self.sampled |= not g.exhaustive
            for (t, extra), r in zip(ts, res):
                out[t] = self._add(r, extra)
        return out

    def _merge(self, terms):
        """Add up repeated terms, so V(a) − V(a) is exactly 0 rather than the width of a's range."""
        w = {}
        for kind, what, k in terms:
            if kind == "v" and what == self.gnd:
                continue
            w[(kind, what)] = w.get((kind, what), 0.0) + k
        return [(kind, what, k) for (kind, what), k in w.items() if k != 0.0]

    @staticmethod
    def _add(a, b):
        return Bound(a.lo + b.lo, a.hi + b.hi, "dc" if a.kind == b.kind == "dc" else "wave", a.loose or b.loose)

    def _term_nodes(self, terms, active, fixed):
        for kind, what, _ in terms:
            if kind == "v":
                yield what
            elif kind == "r":
                yield from self.circ.element(what).nodes[:2]
            elif kind == "i":
                yield what
                for e in active:
                    if what in e.nodes and not (e.kind == "R" and all(self._fx(n, fixed) for n in e.nodes)):
                        yield from e.nodes

    def _range(self, n, fixed, subs):
        if n == self.gnd:
            return Bound(0.0, 0.0, "dc", False)
        s = fixed[n]
        return Bound(s.lo, s.hi, "dc" if s.kind == "dc" else "wave", n in subs)

    def _r_direct(self, e, k, fixed, subs):
        """The current through a resistor between two fixed nodes."""
        a, b = self._range(e.nodes[0], fixed, subs), self._range(e.nodes[1], fixed, subs)
        vlo, vhi = a.lo - b.hi, a.hi - b.lo
        cands = [k * v / r for v in (vlo, vhi) for r in (e.value * (1 - e.tol), e.value * (1 + e.tol))]
        return Bound(min(cands), max(cands), "dc" if a.kind == b.kind == "dc" else "wave", a.loose or b.loose)

    def _direct(self, terms, fixed, subs):
        """A target that only touches fixed nodes: interval arithmetic on their ranges."""
        total = Bound(0.0, 0.0, "dc", False)
        for kind, what, k in terms:
            if kind == "v":
                r = self._range(what, fixed, subs)
                total = self._add(total, Bound(min(k * r.lo, k * r.hi), max(k * r.lo, k * r.hi), r.kind, r.loose))
            elif kind == "r":
                total = self._add(total, self._r_direct(self.circ.element(what), k, fixed, subs))
        return total

    def gain(self, inputs, node, f):
        """|H| from the given fixed nodes, driven together in phase, to a node at f: (min, max) over corners."""
        g = self._group([node], self.fixed, self.sw, extra_fixed=inputs)
        H = g.h_at([[("v", node, 1)]], f)[:, 0, :]
        cols = [g.fixed.index(i) for i in inputs]
        mag = np.abs(np.sum(H[:, cols], axis=1))
        self.sampled |= not g.exhaustive
        return float(np.min(mag)), float(np.max(mag))

    def impedance(self, node, exclude, band):
        """The lowest |Z| seen at a node over a band, with the given elements removed and every source at 0 V."""
        g = self._group([node], self.fixed, self.sw, exclude=exclude, probes=[node])
        Hmin = g.h_band_min([[("v", node, 1)]], band)[:, 0, len(g.fixed)]
        self.sampled |= not g.exhaustive
        return float(np.min(Hmin))

    def worst_input(self, terms, side, sw):
        """What drives a target furthest one way in the linear circuit (no clamp conducting): the starting point for
        a simulation that looks for a real counterexample. side is +1 (push the target up) or −1.

        Returns (inputs, values, settle). inputs maps each source that reaches the target to ("dc", v),
        ("tone", f, phase in degrees) or ("pwl", [(t, v), ...]); a pwl input is the bang-bang waveform that reaches
        the bound at its last point, and every tone peaks together. values are the part values at the worst
        tolerance corner. settle is the slowest time constant in the target's group, in seconds."""
        fixed = self.circ.fixed
        terms = self._merge(terms)
        nodes = set(self._term_nodes(terms, self._active(fixed, sw), fixed))
        free = [n for n in nodes if not self._fx(n, fixed)]
        if not free:
            return {}, {}, 0.0
        g = self._group(free, fixed, sw, extra_fixed=[n for n in nodes if n in fixed])
        J = len(g.fixed)
        stims = [fixed[f] for f in g.fixed]
        modal = g._modal([terms])
        L = g.l1([terms])[:, 0, :J]
        bands = {s.band for s in stims if s.kind == "tone"}
        Hb = {band: g.h_band([terms], band)[:, 0, :J] for band in bands}
        scores, h0s = [], []
        for c, (lam, a, b, d) in enumerate(modal):
            h0 = d[0, :J].real if lam is None else (d[0, :J] - (a[0][:, None] * b[:, :J] / lam[:, None]).sum(0)).real
            h0s.append(h0)
            score = 0.0
            for j, st in enumerate(stims):
                k = side * h0[j]
                if st.kind == "dc":
                    score += max(k * st.lo, k * st.hi)
                elif st.kind == "wave":
                    score += k * st.mid + L[c, j] * st.amp
                else:
                    score += k * st.mid + Hb[st.band][c, j] * st.amp
            scores.append(score)
        c = int(np.argmax(scores))
        vals, lam, a, b, d = (g._dyn_data()[c][0],) + modal[c]
        h0 = h0s[c]
        inputs = {}
        tones = [j for j, st in enumerate(stims) if st.kind == "tone" and st.amp > 0]
        if tones:
            band = (min(stims[j].band[0] for j in tones), max(stims[j].band[1] for j in tones))
            w = g._freqs(band, [lam])
            if lam is None:
                H = np.repeat(d[0, :J, None], len(w), axis=1)
            else:
                H = d[0, :J, None] + np.einsum("k,kj,kf->jf", a[0], b[:, :J], 1.0 / (1j * w[None, :] - lam[:, None]))
            best = int(np.argmax(sum(np.abs(H[j]) * stims[j].amp for j in tones)))
            for j in tones:
                phase = 90.0 - math.degrees(np.angle(H[j, best])) + (0.0 if side > 0 else 180.0)
                inputs[g.fixed[j]] = ("tone", float(w[best] / (2 * math.pi)), phase % 360.0)
        for j, st in enumerate(stims):
            if st.kind == "dc" and st.hi > st.lo and abs(h0[j]) > 1e-12:
                inputs[g.fixed[j]] = ("dc", st.hi if side * h0[j] > 0 else st.lo)
            elif st.kind == "wave" and st.amp > 0 and (L[c, j] > 1e-12 or abs(h0[j]) > 1e-12):
                inputs[g.fixed[j]] = ("pwl", _bang_bang(lam, a, b, d, j, st, side))
        settle = 0.0 if lam is None else 1.0 / max(np.min(-lam.real), 1e-12)
        return inputs, vals, settle

    # -- the nonlinear iteration

    def _node_ranges(self, fixed, sw):
        free = [n for n in self.nodes if n not in fixed]
        res = self.bound([[("v", n, 1)] for n in free], fixed, sw)
        ranges = {n: (r.lo, r.hi, r.kind) for n, r in zip(free, res)}
        for n in self.nodes:
            if n in fixed:
                s = fixed[n]
                ranges[n] = (s.lo, s.hi, "dc" if s.kind == "dc" else "wave")
        ranges[self.gnd] = (0.0, 0.0, "dc")
        return ranges

    def clamp_current(self, c, fixed=None, sw=None):
        """The most current clamp c can carry: the current into its node when held at the clamp voltage. Returns
        (current, loose).

        With no arguments it uses the current branch, without the substitutions made for c's own node or for other
        diode clamps. Those other clamps draw current away from the circuit when they conduct, so leaving them out
        mostly overstates c's current; keeping them would treat their nodes as independent sources, which
        overstates it far more. Amplifier output limits stay in."""
        if fixed is None:
            limited = {n for n, names in self.subs.items() if any(getattr(self.circ.element(x), "limiter", False) for x in names)}
            fixed = {n: s for n, s in self.fixed.items()
                     if n in self.circ.fixed or (n in limited and n not in c.nodes)}
            sw = self.sw
        a, b = c.nodes
        ranges = self._node_ranges_cache
        if self._fx(a, fixed) and self._fx(b, fixed):
            # Held between two fixed nodes: only the conduction voltage limits the current.
            return (math.inf if ranges[a][1] - ranges[b][0] > c.vmin else 0.0), False
        pinned = dict(fixed)
        if not self._fx(a, fixed):
            other = ranges[b]
            pinned[a] = dc(other[0] + c.vmin, other[1] + c.vmin)
            r = self.bound([[("i", a, 1)]], pinned, sw, pinned=[a])[0]
            return max(0.0, r.hi), r.loose
        other = ranges[a]
        pinned[b] = dc(other[0] - c.vmin, other[1] - c.vmin)
        r = self.bound([[("i", b, 1)]], pinned, sw, pinned=[b])[0]
        return max(0.0, -r.lo), r.loose

    def _clamp_fixpoint(self, sw):
        fixed = dict(self.circ.fixed)
        subs = {}
        for _ in range(len(self.clamps) + 2):
            ranges = self._node_ranges(fixed, sw)
            self._node_ranges_cache = ranges
            new, why = {}, {}
            cands = [c for c in self.clamps if not (self._fx(c.nodes[0], fixed) and self._fx(c.nodes[1], fixed))]
            diffs = self.bound([[("v", c.nodes[0], 1.0), ("v", c.nodes[1], -1.0)] for c in cands], fixed, sw)
            for c, d in zip(cands, diffs):
                a, b = c.nodes
                ra, rb = ranges[a], ranges[b]
                if d.hi <= c.vmin:
                    continue
                node = a if not self._fx(a, fixed) else b
                lo, hi, kind = new.get(node, ranges[node])
                i, _ = self.clamp_current(c, fixed, sw)
                extra = c.r_dyn * i if math.isfinite(i) else 0.0
                if node == a:
                    hi = min(hi, rb[1] + c.vmax + extra)
                else:
                    lo = max(lo, ra[0] - c.vmax - extra)
                new[node] = (lo, max(lo, hi), kind)
                why.setdefault(node, []).append(c.name)
            if not new:
                break
            for node, (lo, hi, kind) in new.items():
                fixed[node] = Stim("dc" if kind == "dc" else "wave", lo, hi)
                subs[node] = why[node]
        self._node_ranges_cache = self._node_ranges(fixed, sw)
        return fixed, subs

    def _switch_state(self, s, fixed, sw):
        d, src, g = s.nodes
        lo, hi = self.bound([[("v", g, 1.0), ("v", src, -1.0)]], fixed, sw)[0][:2]
        if s.polarity < 0:
            lo, hi = -hi, -lo
        if lo >= s.vth[1]:
            return "on"
        if hi <= s.vth[0]:
            return "off"
        return "both"

    def run(self):
        """Settle the clamps and switches. Returns a list of branches (one per combination of switches whose gate can
        sit either side of the threshold), each with its fixed nodes, substitutions and switch states."""
        self.branches = []
        self._explore({})
        if not self.branches:
            raise RuntimeError("no consistent switch states")
        return self.branches

    def _explore(self, forced, depth=0):
        if depth > 4:
            raise RuntimeError("too many switches with an undetermined gate")
        sw = {s.name: forced.get(s.name, "off") for s in self.switches}
        for _ in range(10):
            fixed, subs = self._clamp_fixpoint(sw)
            ranges = self._node_ranges_cache
            new, ambiguous = {}, []
            for s in self.switches:
                if s.name in forced:
                    new[s.name] = forced[s.name]
                    continue
                st = self._switch_state(s, fixed, sw)
                if st == "both":
                    ambiguous.append(s.name)
                    st = sw[s.name]
                new[s.name] = st
            if new == sw:
                if ambiguous:
                    for combo in itertools.product(("on", "off"), repeat=len(ambiguous)):
                        self._explore(dict(forced, **dict(zip(ambiguous, combo))), depth + 1)
                    return
                self.branches.append({"fixed": fixed, "subs": subs, "sw": dict(sw), "ranges": ranges,
                                      "forced": dict(forced)})
                return
            sw = new
        raise RuntimeError("switch states didn't settle")

    def use(self, branch):
        """Point bound()/gain()/impedance() at one branch's fixed nodes and switch states."""
        self.fixed, self.sw, self.subs = branch["fixed"], branch["sw"], branch["subs"]
        self._node_ranges_cache = branch["ranges"]
