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


def _linked_image_nodes(socket):
    """Yield image texture nodes connected upstream of a shader socket."""
    seen = set()

    def visit(current_socket):
        for link in current_socket.links:
            node = link.from_node
            pointer = node.as_pointer()
            if pointer in seen:
                continue
            seen.add(pointer)
            if node.type == "TEX_IMAGE":
                yield node
                continue
            for input_socket in node.inputs:
                if input_socket.is_linked:
                    yield from visit(input_socket)

    yield from visit(socket)


def _normalize_glb_texture_samplers():
    """Align samplers for channels glTF must store in one texture.

    glTF has one sampler for the combined base-color/alpha texture and one
    sampler for the combined metallic/roughness texture. Blender's exporter
    chooses the first image node's sampler when these channels use different
    image nodes. Use the primary channel's sampler consistently so the result
    does not depend on node traversal order.
    """
    sampler_properties = ("interpolation", "extension", "projection", "projection_blend")
    channel_groups = (("Base Color", "Alpha"), ("Metallic", "Roughness"))

    for material in bpy.data.materials:
        if not material.use_nodes or material.node_tree is None:
            continue
        for shader in material.node_tree.nodes:
            if shader.type != "BSDF_PRINCIPLED":
                continue
            for primary_name, companion_name in channel_groups:
                primary_socket = shader.inputs.get(primary_name)
                companion_socket = shader.inputs.get(companion_name)
                if primary_socket is None or companion_socket is None:
                    continue
                primary_nodes = list(_linked_image_nodes(primary_socket))
                if not primary_nodes:
                    continue
                reference = primary_nodes[0]
                for image_node in _linked_image_nodes(companion_socket):
                    if image_node == reference:
                        continue
                    changed = []
                    for prop in sampler_properties:
                        if hasattr(reference, prop) and hasattr(image_node, prop):
                            value = getattr(reference, prop)
                            if getattr(image_node, prop) != value:
                                setattr(image_node, prop, value)
                                changed.append(prop)
                    if changed:
                        print(
                            f"Normalized {material.name} {companion_name} texture sampler "
                            f"to match {primary_name} ({', '.join(changed)}).",
                            flush=True,
                        )


def _export_glb(output_path):
    _normalize_glb_texture_samplers()
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
