import bpy
import os

DRACO_COMPRESS_LEVEL = 6
DRACO_QUANTIZATION_SETTINGS = (16, 12, 20, 12)
UNIT_TO_METERS = {"mm": 0.001, "cm": 0.01, "in": 0.0254, "m": 1.0}


def unit_to_meters(unit):
    try:
        return UNIT_TO_METERS[unit.lower()]
    except (AttributeError, KeyError):
        raise ValueError(f"Unsupported scale unit '{unit}'; expected mm, cm, in, or m")


def _scale_imported_model(scale_factor):
    """Scale only hierarchy roots so parented model parts are not scaled twice."""
    if scale_factor == 1.0:
        return
    for obj in bpy.context.scene.objects:
        if obj.parent is None:
            obj.scale = tuple(component * scale_factor for component in obj.scale)


def _export_glb(output_path):
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        export_materials='EXPORT',
        export_normals=True,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=DRACO_COMPRESS_LEVEL,
        export_draco_position_quantization=DRACO_QUANTIZATION_SETTINGS[0],
        export_draco_normal_quantization=DRACO_QUANTIZATION_SETTINGS[1],
        export_draco_texcoord_quantization=DRACO_QUANTIZATION_SETTINGS[2],
        export_draco_generic_quantization=DRACO_QUANTIZATION_SETTINGS[3],
    )

#empty scene to prevent loading old stuff.
def empty_blender_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def apply_draco_compression(output_path, scale_factor=1.0):
    empty_blender_scene()
    try:
        bpy.ops.import_scene.gltf(filepath=output_path)
    except Exception as exc:
        raise RuntimeError(
            f"Blender could not import FreeCAD's intermediate GLB '{output_path}': {exc}"
        ) from exc

    meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.data is not None and len(obj.data.polygons) > 0
    ]
    if not meshes:
        raise RuntimeError(
            f"FreeCAD's intermediate GLB '{output_path}' contains no mesh geometry; "
            "the CAD import/export produced an empty scene"
        )

    _scale_imported_model(scale_factor)
    _export_glb(output_path)

#converts .obj files to .glb.
def convert_obj(file_path, output_path, scale_factor=1.0):
    empty_blender_scene()
    bpy.ops.wm.obj_import(filepath=file_path)
    _scale_imported_model(scale_factor)
    _export_glb(output_path)


#converts .fbx files to .glb.
def convert_fbx(file_path, output_path, scale_factor=1.0):
    empty_blender_scene()
    bpy.ops.wm.fbx_import(filepath=file_path)
    _scale_imported_model(scale_factor)
    _export_glb(output_path)

#converts .stl files to .glb.
def convert_stl(file_path, output_path, scale_factor=1.0):
    empty_blender_scene()
    bpy.ops.wm.stl_import(filepath=file_path)
    _scale_imported_model(scale_factor)
    _export_glb(output_path)

def process_glb_gltf(file_path, output_path):
    empty_blender_scene()
    bpy.ops.import_scene.gltf(filepath=file_path)
    # Existing GLB/GLTF coordinates are already authored in meters. Re-export
    # for consistent Draco compression without applying the input-unit scale.
    _export_glb(output_path)


def convert_non_cad(file_path, file_type, scale_factor=1.0):
    try:
        output_path = os.environ.get("OUTPUT_PATH")
        if not output_path:
            raise RuntimeError("OUTPUT_PATH is not configured")
        if file_type == ".obj":
            convert_obj(file_path, output_path, scale_factor)
        elif file_type == ".fbx":
            convert_fbx(file_path, output_path, scale_factor)
        elif file_type == ".stl":
            convert_stl(file_path, output_path, scale_factor)
        elif file_type in (".glb", ".gltf"):
            process_glb_gltf(file_path, output_path)
        else:
            raise ValueError(f"Unsupported 3D model type: {file_type}")
    finally:
        empty_blender_scene()
