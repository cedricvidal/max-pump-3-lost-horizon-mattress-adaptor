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

Printed mattress tip down, pump plug up: no supports, no overhang over 45 deg.

The original model is not redistributed here. To overlay it for comparison,
download its STL into source/; the reference import is skipped otherwise.

Run inside Blender (via the Blender MCP or `blender -b -P build_adaptor.py`).
All dimensions in mm; 1 Blender unit = 1 mm.
"""
import math
import os

import bmesh
import bpy

ROOT = globals().get("ROOT") or os.path.dirname(os.path.abspath(__file__))
REFERENCE_STL = os.path.join(ROOT, "source", "Ikea Vacuum Bag adapter for Flextail.stl")
OUT_STL = os.path.join(ROOT, "out", "max-pump-3_lost-horizon_adaptor.stl")
OUT_BLEND = os.path.join(ROOT, "max-pump-3-lost-horizon-adaptor.blend")

# Mattress nozzle (bottom, tip on the bed), measured on the original pump.
NOZZLE_OD_TIP = 33.00
NOZZLE_OD_BASE = 33.25
NOZZLE_ID = 29.0
NOZZLE_H = 8.7
NOZZLE_CHAMFER = 0.5

# Shoulder flange: stops the nozzle in the valve. Its underside is a 45 deg
# flare so it prints without supports.
FLANGE_OD = 38.0
FLANGE_H = 2.0

# Cone from the flange down to the pump collar.
CONE_H = 8.0
BORE_CONE_H = 10.0  # inner bore narrows from NOZZLE_ID to PLUG_ID over this height

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
    z_flare_top = z_nozzle_top + (FLANGE_OD - NOZZLE_OD_BASE) / 2  # 45 deg
    z_flange_top = z_flare_top + FLANGE_H
    z_collar = z_flange_top + CONE_H
    z_plug = z_collar + COLLAR_H
    z_top = z_plug + PLUG_H
    return z_nozzle_top, z_flare_top, z_flange_top, z_collar, z_plug, z_top


def profile():
    """Closed half-section (r, z) outline, counter-clockwise."""
    z_nozzle_top, z_flare_top, z_flange_top, z_collar, z_plug, z_top = heights()
    r_plug_base, r_plug_tip = PLUG_OD_BASE / 2, PLUG_OD_TIP / 2
    r_plug_chamfer = r_plug_base + (r_plug_tip - r_plug_base) * (PLUG_H - PLUG_CHAMFER) / PLUG_H
    r_nozzle_tip, r_nozzle_base = NOZZLE_OD_TIP / 2, NOZZLE_OD_BASE / 2
    r_nozzle_chamfer = r_nozzle_tip + (r_nozzle_base - r_nozzle_tip) * NOZZLE_CHAMFER / NOZZLE_H
    return [
        (NOZZLE_ID / 2, 0.0),
        (r_nozzle_tip - NOZZLE_CHAMFER, 0.0),
        (r_nozzle_chamfer, NOZZLE_CHAMFER),
        (r_nozzle_base, z_nozzle_top),
        (FLANGE_OD / 2, z_flare_top),
        (FLANGE_OD / 2, z_flange_top),
        (COLLAR_OD / 2, z_collar),
        (COLLAR_OD / 2, z_plug),
        (r_plug_base, z_plug),
        (r_plug_chamfer, z_top - PLUG_CHAMFER),
        (r_plug_tip - PLUG_CHAMFER, z_top),
        (PLUG_ID / 2, z_top),
        (PLUG_ID / 2, z_nozzle_top + BORE_CONE_H),
        (NOZZLE_ID / 2, z_nozzle_top),
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
    ref.location.z = heights()[3] - 48.0
    for c in list(ref.users_collection):
        c.objects.unlink(ref)
    coll.objects.link(ref)
    return ref


def build_adaptor():
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in profile()]
    edges = [bm.edges.new((verts[i], verts[(i + 1) % len(verts)])) for i in range(len(verts))]
    bmesh.ops.spin(
        bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
        angle=2 * math.pi, steps=SEGMENTS, use_duplicate=False,
    )
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.get("Adaptor") or bpy.data.meshes.new("Adaptor")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.get("Adaptor") or bpy.data.objects.new("Adaptor", mesh)
    obj.data = mesh
    coll = collection("Adaptor")
    if obj.name not in coll.objects:
        coll.objects.link(obj)
    return obj


def verify(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()

    def diameter_at(z, outer=True, below=math.inf):
        rs = [math.hypot(v.co.x, v.co.y) for v in obj.data.vertices if abs(v.co.z - z) < 1e-3]
        rs = [r for r in rs if r < below]
        return round(2 * (max(rs) if outer else min(rs)), 3)

    co = [v.co for v in obj.data.vertices]
    size = [max(c[i] for c in co) - min(c[i] for c in co) for i in range(3)]
    z_nozzle_top, _, z_flange_top, _, z_plug, z_top = heights()
    return {
        "dimensions": [round(d, 3) for d in size],
        "non_manifold_edges": non_manifold,
        "nozzle_od_above_chamfer": diameter_at(NOZZLE_CHAMFER),
        "nozzle_od_base": diameter_at(z_nozzle_top),
        "nozzle_id": diameter_at(0.0, outer=False),
        "flange_od": diameter_at(z_flange_top),
        "plug_od_base": diameter_at(z_plug, below=COLLAR_OD / 2 - 0.01),
        "plug_od_below_chamfer": diameter_at(z_top - PLUG_CHAMFER),
        "plug_id": diameter_at(z_top, outer=False),
    }


def export(obj):
    os.makedirs(os.path.dirname(OUT_STL), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=OUT_STL, export_selected_objects=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


setup_scene()
import_reference()
adaptor = build_adaptor()
result = verify(adaptor)
export(adaptor)
result["stl"] = OUT_STL
