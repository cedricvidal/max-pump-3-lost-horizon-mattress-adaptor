"""Flextail Max Pump 3 -> Lost Horizon mattress adaptor.

Remix of MakerWorld 2165161 "IKEA vacuum bag adapter for Flextail Max Pump 3"
(https://makerworld.com/en/models/2165161): keeps its pump plug (collar + short
tube pushed into the pump's port) and replaces its IKEA valve socket with a
replica of the original Lost Horizon pump nozzle.

Measurements (calipers, see pictures/):
- Pump plug, from a Flextail nozzle attachment: 23.96 mm OD at the collar,
  23.85 mm at the tip, sticking out 3.70 mm past the collar.
- Mattress nozzle, from the original Lost Horizon pump: 33.25 mm OD at the
  shoulder, 33.00 mm at the tip, 8.70 mm long.

NOZZLE_FIT_OFFSET and PLUG_FIT_OFFSET adjust each press-fit diameter to allow
for how FDM parts actually print; the measured values above stay untouched.
Fit-test rings at NOZZLE_TEST_OFFSETS / PLUG_TEST_OFFSETS are exported to
out/fit-test/ to pick each offset with a quick print before printing the full
adaptor. Each ring is marked with one notch per 0.1 mm of offset, cut into the
stop ring / collar edge where it doesn't touch the valve or the pump:
narrow notches = smaller than measured, wide notches = larger, none = 0.0.

Labels are engraved 0.5 mm deep and generated from the tip diameters, so they
always match the print: "MAX PUMP 3 <plug tip> MM" around the top of the cone, "LOST HORIZON <nozzle tip> MM" on the stop ring. They use macOS's Arial
Black (LABEL_FONT); elsewhere Blender's thinner built-in font is used.

Printed mattress tip down, pump plug up: no supports needed.

The original model is not redistributed here. To overlay it for comparison,
download its STL into source/; the reference import is skipped otherwise.

Run inside Blender (via the Blender MCP or `blender -b -P build_adaptor.py`).
All dimensions in mm; 1 Blender unit = 1 mm.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix

ROOT = globals().get("ROOT") or os.path.dirname(os.path.abspath(__file__))
REFERENCE_STL = os.path.join(ROOT, "source", "Ikea Vacuum Bag adapter for Flextail.stl")
OUT_STL = os.path.join(ROOT, "out", "max-pump-3_lost-horizon_adaptor.stl")
OUT_BLEND = os.path.join(ROOT, "max-pump-3-lost-horizon-adaptor.blend")
OUT_FIT_TEST = os.path.join(ROOT, "out", "fit-test")

# Diameter offsets applied to the press-fit parts (nozzle and plug OD).
# From the fit-test rings (0 / -0.1 / -0.2 / +0.1 / +0.2) on the real parts,
# +0.1 fit best on both the mattress valve and the pump.
NOZZLE_FIT_OFFSET = 0.1
PLUG_FIT_OFFSET = 0.1
NOZZLE_TEST_OFFSETS = (0.0, -0.1, -0.2, 0.1, 0.2)
PLUG_TEST_OFFSETS = (0.0, -0.1, -0.2, 0.1, 0.2)

# Fit-test marks: (width mm, spacing deg) for smaller / larger than measured.
NOTCH_NARROW = (1.5, 15.0)
NOTCH_WIDE = (3.5, 30.0)
NOTCH_DEPTH = 0.8

# Engraved labels, derived from the tip diameters so they match the print.
ENGRAVE_DEPTH = 0.5
# A heavy font so engraved strokes are wide enough to print; falls back to
# Blender's built-in font if it isn't installed.
LABEL_FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
PUMP_LABEL_H = 2.8      # cap height, on the cone just below the collar
PUMP_LABEL_GAP = 0.8    # between the label and the collar
MAX_LABEL_SPAN = 300.0  # degrees; leaves a gap so a label never runs into itself
MATTRESS_LABEL_H = 2.6  # cap height, on the side of the stop ring

# Mattress nozzle (bottom, tip on the bed), measured on the original pump.
NOZZLE_OD_TIP = 33.00
NOZZLE_OD_BASE = 33.25
NOZZLE_ID = 29.0
NOZZLE_H = 8.7
NOZZLE_CHAMFER = 0.5

# Stop ring behind the nozzle: thin and square like the original pump's
# (estimated from pictures/original-*.jpeg). The ~0.9 mm underside ledge
# prints without supports.
STOP_OD = 35.0
STOP_H = 3.5

# Cone from the stop ring to the pump collar. The bore follows it with a
# constant wall (measured square to the surface) to save material.
CONE_H = 8.0
CONE_WALL = 2.0

# Pump collar and plug (top), collar as on the IKEA adapter, plug measured.
COLLAR_OD = 28.0
COLLAR_H = 2.0
PLUG_OD_BASE = 23.96
PLUG_OD_TIP = 23.85
PLUG_ID = 20.0
PLUG_H = 3.7
PLUG_CHAMFER = 0.3

SEGMENTS = 128


def heights():
    z_nozzle_top = NOZZLE_H
    z_stop_top = z_nozzle_top + STOP_H
    z_collar = z_stop_top + CONE_H
    z_plug = z_collar + COLLAR_H
    z_top = z_plug + PLUG_H
    return z_nozzle_top, z_stop_top, z_collar, z_plug, z_top


def nozzle_outline(fit):
    """Outer nozzle edge from the tip (z=0) up to its base."""
    r_tip, r_base = (NOZZLE_OD_TIP + fit) / 2, (NOZZLE_OD_BASE + fit) / 2
    r_chamfer = r_tip + (r_base - r_tip) * NOZZLE_CHAMFER / NOZZLE_H
    return [(r_tip - NOZZLE_CHAMFER, 0.0), (r_chamfer, NOZZLE_CHAMFER), (r_base, NOZZLE_H)]


def plug_outline(fit, z_plug):
    """Outer plug edge from its base (z_plug) up to its tip."""
    r_base, r_tip = (PLUG_OD_BASE + fit) / 2, (PLUG_OD_TIP + fit) / 2
    r_chamfer = r_base + (r_tip - r_base) * (PLUG_H - PLUG_CHAMFER) / PLUG_H
    z_top = z_plug + PLUG_H
    return [(r_base, z_plug), (r_chamfer, z_top - PLUG_CHAMFER), (r_tip - PLUG_CHAMFER, z_top)]


def bore_outline():
    """Inner bore from the collar top down to the nozzle bore, following the cone."""
    _, z_stop_top, z_collar, z_plug, _ = heights()
    slope = (STOP_OD - COLLAR_OD) / 2 / CONE_H  # radial change per mm of height
    offset = CONE_WALL * math.sqrt(1 + slope**2)  # horizontal offset for a square wall
    r_collar = COLLAR_OD / 2 - offset
    z_meet = z_stop_top + (STOP_OD / 2 - offset - NOZZLE_ID / 2) / slope
    assert z_stop_top <= z_meet <= z_collar, "nozzle bore must meet the cone bore"
    assert r_collar - PLUG_ID / 2 <= COLLAR_H, "collar bore chamfer steeper than 45 deg"
    return [(PLUG_ID / 2, z_plug), (r_collar, z_collar), (NOZZLE_ID / 2, z_meet)]


def profile(nozzle_fit=NOZZLE_FIT_OFFSET, plug_fit=PLUG_FIT_OFFSET):
    """Closed half-section (r, z) outline of the adaptor, counter-clockwise."""
    z_nozzle_top, z_stop_top, z_collar, z_plug, z_top = heights()
    return [
        (NOZZLE_ID / 2, 0.0),
        *nozzle_outline(nozzle_fit),
        (STOP_OD / 2, z_nozzle_top),
        (STOP_OD / 2, z_stop_top),
        (COLLAR_OD / 2, z_collar),
        (COLLAR_OD / 2, z_plug),
        *plug_outline(plug_fit, z_plug),
        (PLUG_ID / 2, z_top),
        *bore_outline(),
    ]


def nozzle_test_profile(fit):
    """Fit-test ring: the mattress nozzle and its stop ring only."""
    z_nozzle_top, z_stop_top = NOZZLE_H, NOZZLE_H + STOP_H
    return [
        (NOZZLE_ID / 2, 0.0),
        *nozzle_outline(fit),
        (STOP_OD / 2, z_nozzle_top),
        (STOP_OD / 2, z_stop_top),
        (NOZZLE_ID / 2, z_stop_top),
    ]


def plug_test_profile(fit):
    """Fit-test ring: the pump collar and plug only."""
    return [
        (PLUG_ID / 2, 0.0),
        (COLLAR_OD / 2, 0.0),
        (COLLAR_OD / 2, COLLAR_H),
        *plug_outline(fit, COLLAR_H),
        (PLUG_ID / 2, COLLAR_H + PLUG_H),
    ]


def collection(name, hide=False):
    coll = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    bpy.context.view_layer.layer_collection.children[coll.name].hide_viewport = hide
    return coll


def setup_scene():
    # Selection and export operators only work in Object Mode.
    if bpy.context.view_layer.objects.active and bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    units = bpy.context.scene.unit_settings
    units.system = "METRIC"
    units.scale_length = 0.001
    units.length_unit = "MILLIMETERS"


def import_reference():
    old = bpy.data.collections.get("Reference")
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    if not os.path.exists(REFERENCE_STL):
        return None
    coll = collection("Reference", hide=True)
    bpy.ops.wm.stl_import(filepath=REFERENCE_STL)
    ref = bpy.context.selected_objects[0]
    ref.name = "Reference_IKEA_Adapter"
    # Deselect now: once hidden, select_all() can't reach it and it would be exported.
    ref.select_set(False)
    # Align its pump collar (z=48 in the original) with ours.
    ref.location.z = heights()[2] - 48.0
    for c in list(ref.users_collection):
        c.objects.unlink(ref)
    coll.objects.link(ref)
    return ref


def revolve(name, outline, coll_name):
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in outline]
    edges = [bm.edges.new((verts[i], verts[(i + 1) % len(verts)])) for i in range(len(verts))]
    bmesh.ops.spin(
        bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
        angle=2 * math.pi, steps=SEGMENTS, use_duplicate=False,
    )
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.get(name) or bpy.data.objects.new(name, mesh)
    obj.data = mesh
    coll = collection(coll_name)
    if obj.name not in coll.objects:
        coll.objects.link(obj)
    return obj


def cut_notches(obj, fit, radius, z0, z1):
    """Mark `obj` with one vertical notch per 0.1 mm of `fit` in the outer face at
    `radius` between z0 and z1: narrow if fit < 0, wide if fit > 0."""
    count = round(abs(fit) * 10)
    if count == 0:
        return
    width, spacing = NOTCH_WIDE if fit > 0 else NOTCH_NARROW
    bm = bmesh.new()
    height = z1 - z0 + 2.0  # overshoot both ends for a clean cut
    for k in range(count):
        angle = math.radians(spacing * (k - (count - 1) / 2))
        matrix = (
            Matrix.Rotation(angle, 4, "Z")
            @ Matrix.Translation((radius, 0.0, (z0 + z1) / 2))
            @ Matrix.Diagonal((2 * NOTCH_DEPTH, width, height, 1.0))
        )
        bmesh.ops.create_cube(bm, size=1.0, matrix=matrix)
    subtract(obj, bm)


def subtract(obj, cutter_bm):
    """Boolean-subtract the geometry in `cutter_bm` from `obj` and apply it."""
    cutter_mesh = bpy.data.meshes.new(obj.name + "_cutter")
    cutter_bm.to_mesh(cutter_mesh)
    cutter_bm.free()
    cutter = bpy.data.objects.new(cutter_mesh.name, cutter_mesh)
    bpy.context.scene.collection.objects.link(cutter)

    boolean = obj.modifiers.new("cut", "BOOLEAN")
    boolean.operation = "DIFFERENCE"
    boolean.solver = "EXACT"
    boolean.use_self = True  # font glyphs can overlap themselves (e.g. Arial Black)
    boolean.object = cutter
    depsgraph = bpy.context.evaluated_depsgraph_get()
    old_mesh = obj.data
    obj.data = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    obj.modifiers.remove(boolean)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(cutter_mesh)
    bpy.data.meshes.remove(old_mesh)
    obj.data.name = obj.name


def orient_outward(bm):
    """Flip any inside-out island (e.g. a glyph) so its signed volume is positive.
    recalc_face_normals guesses wrong on some glyphs, such as Arial Black's "1"."""
    seen = set()
    for start in bm.faces:
        if start in seen:
            continue
        island, stack = [], [start]
        seen.add(start)
        while stack:
            face = stack.pop()
            island.append(face)
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked not in seen:
                        seen.add(linked)
                        stack.append(linked)
        volume = sum(
            loops[0].vert.co.dot(loops[1].vert.co.cross(loops[2].vert.co))
            for loops in (f.loops for f in island)
        )
        if volume < 0:
            bmesh.ops.reverse_faces(bm, faces=island)


def text_solid(body, cap_height):
    """Text as a closed triangulated bmesh: x along the text (centred), y up from
    the baseline (cap height = `cap_height`), z from -1 to 1 through its thickness."""
    curve = bpy.data.curves.new("label", "FONT")
    curve.body = body
    curve.align_x = "CENTER"
    curve.extrude = 1.0
    curve.resolution_u = 4
    if os.path.exists(LABEL_FONT):
        curve.font = bpy.data.fonts.load(LABEL_FONT, check_existing=True)
    text = bpy.data.objects.new("label", curve)
    bpy.context.scene.collection.objects.link(text)
    mesh = bpy.data.meshes.new_from_object(text.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(text, do_unlink=True)
    bpy.data.curves.remove(curve)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bpy.data.meshes.remove(mesh)
    # Font conversion leaves caps and side walls unwelded; the boolean needs a closed solid.
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    assert all(e.is_manifold for e in bm.edges), f"label {body!r} is not a closed solid"
    ys = [v.co.y for v in bm.verts]
    scale = cap_height / (max(ys) - min(ys))  # all caps: glyph extent = cap height
    y0 = min(ys)
    for v in bm.verts:
        v.co.x *= scale
        v.co.y = (v.co.y - y0) * scale
    return bm


LABEL_SPANS = {}  # label -> degrees of the circumference it covers


def engrave(obj, body, cap_height, z_bottom, radius_at, angle=0.0):
    """Engrave `body` ENGRAVE_DEPTH deep into the outer surface of `obj`, wrapped
    around the z axis, letters upright, centred on `angle` (radians from +X).
    `radius_at(z)` gives the outer surface radius at height z."""
    bm = text_solid(body, cap_height)
    overshoot = 0.5
    r_ref = radius_at(z_bottom + cap_height / 2)
    width = max(v.co.x for v in bm.verts) - min(v.co.x for v in bm.verts)
    span = math.degrees(width / r_ref)
    assert span <= MAX_LABEL_SPAN, f"label {body!r} wraps {span:.0f} deg, more than {MAX_LABEL_SPAN:.0f}"
    LABEL_SPANS[body] = round(span)
    for v in bm.verts:
        x, y, t = v.co
        z = z_bottom + y
        r = radius_at(z) - ENGRAVE_DEPTH + (t + 1) / 2 * (ENGRAVE_DEPTH + overshoot)
        theta = angle + x / r_ref
        v.co = (r * math.cos(theta), r * math.sin(theta), z)
    orient_outward(bm)
    subtract(obj, bm)
    assert len(obj.data.vertices) > 0, f"engraving {body!r} destroyed the mesh"


def add_labels(obj):
    """Pump label around the top of the cone, mattress label on the side of the
    stop ring, both centred on +X."""
    z_nozzle_top, z_stop_top, z_collar, _, _ = heights()
    slope = (STOP_OD - COLLAR_OD) / 2 / CONE_H
    cone_radius = lambda z: STOP_OD / 2 - (z - z_stop_top) * slope

    pump = f"MAX PUMP 3 {PLUG_OD_TIP + PLUG_FIT_OFFSET:.2f} MM"
    engrave(obj, pump, PUMP_LABEL_H, z_collar - PUMP_LABEL_GAP - PUMP_LABEL_H, cone_radius)

    mattress = f"LOST HORIZON {NOZZLE_OD_TIP + NOZZLE_FIT_OFFSET:.2f} MM"
    margin = (STOP_H - MATTRESS_LABEL_H) / 2
    engrave(obj, mattress, MATTRESS_LABEL_H, z_nozzle_top + margin, lambda z: STOP_OD / 2)


def build_fit_tests():
    """Nozzle rings and plug rings per test offset, laid out in two rows."""
    z_stop_top = NOZZLE_H + STOP_H
    kinds = (
        ("nozzle", nozzle_test_profile, NOZZLE_TEST_OFFSETS, 0.0, (STOP_OD / 2, z_stop_top - 2.0, z_stop_top)),
        ("plug", plug_test_profile, PLUG_TEST_OFFSETS, 40.0, (COLLAR_OD / 2, 0.0, COLLAR_H)),
    )
    tests = []
    for kind, outline, offsets, y, notch_at in kinds:
        for i, fit in enumerate(offsets):
            obj = revolve(f"fit-test_{kind}_{fit:+.2f}", outline(fit), "FitTest")
            obj.location = (0.0, 0.0, 0.0)
            cut_notches(obj, fit, *notch_at)
            obj.location = (60.0 + 40.0 * i, y, 0.0)
            tests.append(obj)
    return tests


def verify(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    volume = bm.calc_volume()
    bm.free()

    def diameter_at(z, outer=True, below=math.inf):
        rs = [math.hypot(v.co.x, v.co.y) for v in obj.data.vertices if abs(v.co.z - z) < 1e-3]
        rs = [r for r in rs if r < below]
        return round(2 * (max(rs) if outer else min(rs)), 3)

    co = [v.co for v in obj.data.vertices]
    size = [max(c[i] for c in co) - min(c[i] for c in co) for i in range(3)]
    z_nozzle_top, z_stop_top, z_collar, z_plug, z_top = heights()
    return {
        "dimensions": [round(d, 3) for d in size],
        "non_manifold_edges": non_manifold,
        "volume_cm3": round(volume / 1000, 2),
        "nozzle_od_above_chamfer": diameter_at(NOZZLE_CHAMFER),
        "nozzle_od_base": diameter_at(z_nozzle_top, below=STOP_OD / 2 - 0.01),
        "nozzle_id": diameter_at(0.0, outer=False),
        "stop_od": diameter_at(z_stop_top),
        "plug_od_base": diameter_at(z_plug, below=COLLAR_OD / 2 - 0.01),
        "plug_od_below_chamfer": diameter_at(z_top - PLUG_CHAMFER),
        "plug_id": diameter_at(z_top, outer=False),
        "bore_at_collar": diameter_at(z_collar, outer=False),
    }


def export_stl(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    location = obj.location.copy()
    obj.location = (0.0, 0.0, 0.0)  # export each part at the origin
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True)
    obj.location = location


setup_scene()
import_reference()
adaptor = revolve("Adaptor", profile(), "Adaptor")
result = verify(adaptor)
add_labels(adaptor)
result["labels"] = LABEL_SPANS
export_stl(adaptor, OUT_STL)
for test in build_fit_tests():
    export_stl(test, os.path.join(OUT_FIT_TEST, test.name + ".stl"))
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
result["stl"] = OUT_STL
