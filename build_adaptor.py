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

FIT_OFFSET shrinks both press-fit diameters (nozzle and plug) to allow for FDM
parts printing slightly oversize; the measured values above stay untouched.
Fit-test rings at FIT_TEST_OFFSETS are exported to out/fit-test/ to pick the
best offset with a quick print before printing the full adaptor. Each ring is
marked with one notch per 0.1 mm of offset (none for 0.0), cut into the stop
ring / collar edge where it doesn't touch the valve or the pump.

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

# Diameter offset applied to the press-fit parts (nozzle and plug OD).
FIT_OFFSET = -0.1
FIT_TEST_OFFSETS = (0.0, -0.1, -0.2)
NOTCH_WIDTH = 1.5
NOTCH_DEPTH = 0.8
NOTCH_SPACING = 15.0  # degrees between notches

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


def profile(fit=FIT_OFFSET):
    """Closed half-section (r, z) outline of the adaptor, counter-clockwise."""
    z_nozzle_top, z_stop_top, z_collar, z_plug, z_top = heights()
    return [
        (NOZZLE_ID / 2, 0.0),
        *nozzle_outline(fit),
        (STOP_OD / 2, z_nozzle_top),
        (STOP_OD / 2, z_stop_top),
        (COLLAR_OD / 2, z_collar),
        (COLLAR_OD / 2, z_plug),
        *plug_outline(fit, z_plug),
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


def cut_notches(obj, count, radius, z0, z1):
    """Cut `count` vertical notches into the outer face at `radius` between z0 and z1."""
    if count == 0:
        return
    bm = bmesh.new()
    height = z1 - z0 + 2.0  # overshoot both ends for a clean cut
    for k in range(count):
        angle = math.radians(NOTCH_SPACING * (k - (count - 1) / 2))
        matrix = (
            Matrix.Rotation(angle, 4, "Z")
            @ Matrix.Translation((radius, 0.0, (z0 + z1) / 2))
            @ Matrix.Diagonal((2 * NOTCH_DEPTH, NOTCH_WIDTH, height, 1.0))
        )
        bmesh.ops.create_cube(bm, size=1.0, matrix=matrix)
    cutter_mesh = bpy.data.meshes.new(obj.name + "_notches")
    bm.to_mesh(cutter_mesh)
    bm.free()
    cutter = bpy.data.objects.new(cutter_mesh.name, cutter_mesh)
    bpy.context.scene.collection.objects.link(cutter)

    boolean = obj.modifiers.new("notches", "BOOLEAN")
    boolean.operation = "DIFFERENCE"
    boolean.solver = "EXACT"
    boolean.object = cutter
    depsgraph = bpy.context.evaluated_depsgraph_get()
    old_mesh = obj.data
    obj.data = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    obj.modifiers.remove(boolean)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(cutter_mesh)
    bpy.data.meshes.remove(old_mesh)
    obj.data.name = obj.name


def build_fit_tests():
    """One nozzle ring and one plug ring per offset, laid out in a row."""
    tests = []
    for i, fit in enumerate(FIT_TEST_OFFSETS):
        notches = round(-fit * 10)
        for kind, outline, y in (("nozzle", nozzle_test_profile, 0.0), ("plug", plug_test_profile, 40.0)):
            obj = revolve(f"fit-test_{kind}_{fit:+.2f}", outline(fit), "FitTest")
            obj.location = (0.0, 0.0, 0.0)
            if kind == "nozzle":
                z_top = NOZZLE_H + STOP_H
                cut_notches(obj, notches, STOP_OD / 2, z_top - 2.0, z_top)
            else:
                cut_notches(obj, notches, COLLAR_OD / 2, 0.0, COLLAR_H)
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
export_stl(adaptor, OUT_STL)
for test in build_fit_tests():
    export_stl(test, os.path.join(OUT_FIT_TEST, test.name + ".stl"))
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
result["stl"] = OUT_STL
