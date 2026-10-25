"""Bode plot of the rev 1 carrier board's analog paths, with the Daisy treated as an ideal wire.

Each RC / op-amp stage is modelled as a first-order section using BOM values.
The input low-pass assumes ~8 pF at U1A+ (op-amp input + layout) with RV1 at
mid travel; it moves up in frequency as RV1 approaches full.

Run: python3 studies/signal-path-response/phase_response.py
  -> phase_response.png and group_delay.png (same folder)
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def corner(r, c):
    return 1 / (2 * np.pi * r * c)


def par(*rs):
    return 1 / sum(1 / r for r in rs)


def hp(fc):
    return lambda f: (1j * f / fc) / (1 + 1j * f / fc)


def lp(fc):
    return lambda f: 1 / (1 + 1j * f / fc)


# Input: J1 -> C3 -> RV1 -> R1 -> U1A buffer -> AUDIO_IN_1
INPUT = [
    hp(corner(par(1e6, 1e3 + 10e6), 1e-6)),  # C3 into RV1 || (R1 + R5)
    lp(corner(250e3 + 1e3, 8e-12)),          # wiper Thevenin + R1 into U1A Cin (estimate)
]

# Output: AUDIO_OUT_1 -> R2/C2 -> C5/R6 -> U1B -> C12/R9 -> U2 (x-1) -> C14 -> J5 / J2
OUTPUT_COMMON = [
    lp(corner(3.3e3, 1e-9)),     # R2 / C2
    hp(corner(1e6, 1e-6)),       # C5 / R6
    hp(corner(20e3, 4.7e-6)),    # C12 / R9
]
OUTPUT_HP = OUTPUT_COMMON + [hp(corner(par(100, 4.7 + 32), 470e-6))]           # 32 ohm phones
OUTPUT_LINE = OUTPUT_COMMON + [hp(corner(par(100, 4.7 + 100 + 100e3), 470e-6))]  # J2, no plug in J5


def response(stages, f):
    return np.prod([s(f) for s in stages], axis=0)


def group_delay(stages, f):
    phase = np.unwrap(np.angle(response(stages, f)))
    return -np.gradient(phase, 2 * np.pi * f)


# Reference categorical palette, slots 1-3 (validated all-pairs, light mode)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TEXT, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

SERIES = [
    ("Input  (J1 → Daisy)", INPUT, BLUE, "-"),
    ("Output (Daisy → J5, 32 Ω)", OUTPUT_HP, ORANGE, "-"),
    ("Output (Daisy → J2 line)", OUTPUT_LINE, ORANGE, "--"),
    ("End to end (J1 → J5, 32 Ω)", INPUT + OUTPUT_HP, AQUA, "-"),
]

f = np.logspace(0, np.log10(100e3), 2000)

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlecolor": TEXT,
    "axes.titleweight": "bold", "axes.titlelocation": "left",
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})
fig, (ax_mag, ax_ph, ax_gd) = plt.subplots(3, 1, figsize=(10, 11), sharex=True)

for label, stages, color, ls in SERIES:
    h = response(stages, f)
    ax_mag.semilogx(f, 20 * np.log10(np.abs(h)), color=color, ls=ls, lw=2, label=label)
    ax_ph.semilogx(f, np.degrees(np.angle(h)), color=color, ls=ls, lw=2)
    ax_gd.loglog(f, np.abs(group_delay(stages, f)) * 1e6, color=color, ls=ls, lw=2)

ax_mag.set_title("Magnitude")
ax_mag.set_ylabel("dB")
ax_mag.set_ylim(-6, 1)
ax_mag.legend(loc="lower center", frameon=False, ncol=2, labelcolor=TEXT)

ax_ph.set_title("Phase (excluding U2's 180° polarity inversion)")
ax_ph.set_ylabel("degrees")
ax_ph.set_ylim(-60, 90)
ax_ph.axhline(0, color=MUTED, lw=0.8)

ax_gd.set_title("Group delay")
ax_gd.set_ylabel("µs (log)")
ax_gd.set_xlabel("Frequency (Hz)")
ax_gd.set_ylim(1, 1e5)
ax_gd.annotate("≈ 5 µs end to end above ~2 kHz", xy=(5e3, 5.2), xytext=(1.2e3, 40),
               color=TEXT, arrowprops=dict(arrowstyle="-", color=MUTED))

for ax in (ax_mag, ax_ph, ax_gd):
    ax.grid(True, which="both", color=GRID, lw=0.6)
    ax.axvspan(20, 20e3, color=GRID, alpha=0.35, lw=0)  # audio band
    ax.spines[["top", "right"]].set_visible(False)
ax_gd.set_xlim(f[0], f[-1])
ax_mag.text(21, 0.4, "audio band 20 Hz – 20 kHz", color=MUTED, fontsize=9)

fig.suptitle("Seed3 carrier rev 1: analog path response (Daisy treated as ideal)",
             x=0.06, ha="left", fontweight="bold", color=TEXT)
fig.tight_layout()
out = Path(__file__).with_suffix(".png")
fig.savefig(out, dpi=150)
print(f"wrote {out}")

# Group delay on its own, with the end-to-end value marked at 1 kHz and 10 kHz
fig, ax = plt.subplots(figsize=(10, 5.5))
for label, stages, color, ls in SERIES:
    ax.loglog(f, np.abs(group_delay(stages, f)) * 1e6, color=color, ls=ls, lw=2, label=label)

for fr in (1e3, 10e3):
    d = group_delay(INPUT + OUTPUT_HP, np.array([fr * 0.999, fr, fr * 1.001]))[1] * 1e6
    ax.plot(fr, d, "o", ms=8, color=AQUA, mec=SURFACE, mew=2, zorder=5)
    ax.annotate(f"{d:.1f} µs @ {fr / 1e3:g} kHz", (fr, d), xytext=(0, 14),
                textcoords="offset points", ha="center", color=TEXT, fontsize=9)

ax.axvspan(20, 20e3, color=GRID, alpha=0.35, lw=0)  # audio band
ax.text(22, 1.15, "audio band 20 Hz – 20 kHz", color=MUTED, fontsize=9)
ax.text(1.2, 1.6, "Low-frequency rise = coupling-cap phase lead,\nnot an audible time lag",
        color=MUTED, fontsize=9)
ax.grid(True, which="both", color=GRID, lw=0.6)
ax.spines[["top", "right"]].set_visible(False)
ax.set_xlim(f[0], f[-1])
ax.set_ylim(1, 1e5)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel("Group delay (µs, log)")
ax.set_title("Seed3 carrier rev 1: group delay (Daisy treated as ideal)")
ax.legend(loc="upper right", frameon=False, labelcolor=TEXT)
fig.tight_layout()
out = Path(__file__).with_name("group_delay.png")
fig.savefig(out, dpi=150)
print(f"wrote {out}")
