"""Flextail Max Pump 3 -> Lost Horizon mattress adaptor.

Remix of MakerWorld 2165161 "IKEA vacuum bag adapter for Flextail Max Pump 3":
keeps its pump-side socket and replaces the IKEA nozzle with a replica of the
original Lost Horizon pump nozzle (see original-*.jpeg).

Run inside Blender (via the Blender MCP or `blender -P build_adaptor.py`).
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

# Pump socket, measured from the original STL.
SOCKET_OD = 42.0
SOCKET_ID = 35.7
SOCKET_H = 10.0

# Transition cone; its flare is the insertion stop.
CONE_H = 10.0

# Mattress nozzle, measured on the original pump.
NOZZLE_OD_BASE = 33.25
NOZZLE_OD_TIP = 33.00
NOZZLE_ID = 29.0
NOZZLE_H = 8.7
TIP_CHAMFER = 0.5

SEGMENTS = 128


def profile():
    """Closed half-section (r, z) outline, counter-clockwise."""
    z_cone = SOCKET_H
    z_nozzle = SOCKET_H + CONE_H
    z_tip = z_nozzle + NOZZLE_H
    z_chamfer = z_tip - TIP_CHAMFER
    r_base, r_tip = NOZZLE_OD_BASE / 2, NOZZLE_OD_TIP / 2
    r_chamfer = r_base + (r_tip - r_base) * (z_chamfer - z_nozzle) / NOZZLE_H
    return [
        (SOCKET_ID / 2, 0.0),
        (SOCKET_OD / 2, 0.0),
        (SOCKET_OD / 2, z_cone),
        (r_base, z_nozzle),
        (r_chamfer, z_chamfer),
        (r_tip - TIP_CHAMFER, z_tip),
        (NOZZLE_ID / 2, z_tip),
        (NOZZLE_ID / 2, z_nozzle),
        (SOCKET_ID / 2, z_cone),
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
    coll = collection("Reference", hide=True)
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.wm.stl_import(filepath=REFERENCE_STL)
    ref = bpy.context.selected_objects[0]
    ref.name = "Reference_IKEA_Adapter"
    # Deselect now: once hidden, select_all() can't reach it and it would be exported.
    ref.select_set(False)
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

    def radius_at(z, outer=True):
        rs = [math.hypot(v.co.x, v.co.y) for v in obj.data.vertices if abs(v.co.z - z) < 1e-3]
        return round(max(rs) if outer else min(rs), 3)

    z_tip = SOCKET_H + CONE_H + NOZZLE_H
    return {
        "dimensions": [round(d, 3) for d in obj.dimensions],
        "non_manifold_edges": non_manifold,
        "outer_r_socket": radius_at(0.0),
        "inner_r_socket": radius_at(0.0, outer=False),
        "outer_r_nozzle_base": radius_at(SOCKET_H + CONE_H),
        "outer_r_below_chamfer": radius_at(z_tip - TIP_CHAMFER),
        "inner_r_nozzle": radius_at(z_tip, outer=False),
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
