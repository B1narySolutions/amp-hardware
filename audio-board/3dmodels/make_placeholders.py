"""Generate simplified STEP placeholder models for parts with no vendor 3D model.

Bodies are boxes/cylinders sized from the manufacturer drawings so jack and
shaft centrelines land where the real parts will. Internal detail is omitted.

Coordinates are KiCad model space: origin = footprint origin, +Z up from the
board's top surface, and model Y = -(footprint Y).

Run from this directory:
    uv run --python 3.12 --with build123d python make_placeholders.py
"""

from build123d import Align, Axis, Box, Compound, Cylinder, Location, export_step

C = (Align.CENTER, Align.CENTER, Align.MIN)


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from footprint-space X/Y extents (Y is flipped)."""
    return Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN,) * 3).locate(
        Location((x0, -y1, z0))
    )


def cyl_x(x0, x1, y, z, d):
    """Cylinder along +X from x0 to x1, axis at footprint (y, z)."""
    return Cylinder(d / 2, x1 - x0, align=C).locate(
        Location((x0, -y, z), (0, 90, 0))
    )


def cyl_y(y0, y1, x, z, d):
    """Cylinder along footprint -Y from y0 down to y1 (y1 < y0)."""
    return Cylinder(d / 2, y0 - y1, align=C).locate(
        Location((x, -y0, z), (-90, 0, 0))
    )


def cyl_z(x, y, z0, z1, d):
    return Cylinder(d / 2, z1 - z0, align=C).locate(Location((x, -y, z0)))


def save(name, *solids):
    export_step(Compound(list(solids)), f"{name}.step")
    print("wrote", f"{name}.step")


# Neutrik NRJ4HF, drawing ST-NRJ4HF: body 24.3 x 15.75 x 12.7 tall, axis 6.5 above
# PCB, threaded nose 8.9 long. Panel cutout is 11.2, so the nose is ~11 OD.
nrj_axis_y = 13.66 - 6.43
save(
    "Neutrik_NRJ4HF_placeholder",
    box(-7.35, 16.95, -2.09, 13.66, 0, 12.7),
    cyl_x(16.95, 25.85, nrj_axis_y, 6.5, 11.0),
)

# Same Sky SJ1-3535NG, datasheet SJ1-353XNG rev 1.06: body 14 x 8.2 x 12.5 tall,
# axis 7.0 above PCB and 4.9 from the -X side, nose OD 6.0 x 4.0 long.
save(
    "SameSky_SJ1-3535NG_placeholder",
    box(-4.0, 4.2, -1.2, 12.8, 0, 12.5),
    cyl_y(-1.2, -5.2, -4.0 + 4.9, 7.0, 6.0),
)

# Bourns PTV09A-4020F (rear mount, bushingless, 20 mm F-type shaft): ~6 mm body,
# mounting face at 7 mm, shaft Ø6 extends L=20 beyond it. Flat (F=7 long,
# 4.5 across) is omitted; orient knobs in CAD.
pot_shaft = (7.0, -2.5)
save(
    "Bourns_PTV09A-4020F_placeholder",
    box(1.0, 13.0, -7.35, 2.35, 0, 6.0),
    cyl_z(*pot_shaft, 6.0, 7.0, 7.0),
    cyl_z(*pot_shaft, 7.0, 27.0, 6.0),
)

# Electrosmith Daisy Seed: 51 x 18 x 1.6 PCB, plugged into two 8.5 mm 1x20
# female sockets (modelled separately on the A1 footprint) so it can be swapped.
# Its own male headers add a 2.5 mm plastic spacer on top of the sockets.
# Components treated as a 2 mm envelope; micro-USB sits at the pin 1/40 end and
# overhangs ~1 mm.
socket_h = 8.5
pcb_z0 = socket_h + 2.5
pcb_z1 = pcb_z0 + 1.6
save(
    "Electrosmith_Daisy_Seed_placeholder",
    box(-1.27, 1.27, -1.27, 49.53, socket_h, pcb_z0),
    box(13.97, 16.51, -1.27, 49.53, socket_h, pcb_z0),
    box(-1.38, 16.62, -1.38, 49.62, pcb_z0, pcb_z1),
    box(1.5, 13.7, 3.0, 47.0, pcb_z1, pcb_z1 + 2.0),
    box(7.62 - 4.0, 7.62 + 4.0, -2.4, 3.3, pcb_z1, pcb_z1 + 3.0),
)
