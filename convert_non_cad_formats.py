import bpy
import os

DRACO_COMPRESS_LEVEL = 6
DRACO_QUANTIZATION_SETTINGS = (16,12,12,12)

#empty scene to prevent loading old stuff.
def empty_blender_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def apply_draco_compression(output_path):
    empty_blender_scene()
    bpy.ops.import_scene.gltf(filepath=output_path)
    bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB', export_materials='EXPORT', export_normals=True,
                              export_draco_mesh_compression_enable=True,
                                export_draco_mesh_compression_level=DRACO_COMPRESS_LEVEL,
                                export_draco_position_quantization=DRACO_QUANTIZATION_SETTINGS[0], 
                                export_draco_normal_quantization=DRACO_QUANTIZATION_SETTINGS[1],
                                export_draco_texcoord_quantization=DRACO_QUANTIZATION_SETTINGS[2],
                                export_draco_generic_quantization=DRACO_QUANTIZATION_SETTINGS[3])

#converts .obj files to .glb.
def convert_obj(file_path, output_path):
    empty_blender_scene()
    bpy.ops.wm.obj_import(filepath=file_path)
    bpy.ops.export_scene.gltf(  filepath=output_path, export_format='GLB', 
                                export_draco_mesh_compression_enable=True,
                                export_draco_mesh_compression_level=DRACO_COMPRESS_LEVEL,
                                export_draco_position_quantization=DRACO_QUANTIZATION_SETTINGS[0], 
                                export_draco_normal_quantization=DRACO_QUANTIZATION_SETTINGS[1],
                                export_draco_texcoord_quantization=DRACO_QUANTIZATION_SETTINGS[2],
                                export_draco_generic_quantization=DRACO_QUANTIZATION_SETTINGS[3]
                              )


#converts .fbx files to .glb.
def convert_fbx(file_path, output_path):
    empty_blender_scene()
    bpy.ops.wm.fbx_import(filepath=file_path)
    bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB', export_materials='EXPORT', export_normals=True,
                              export_draco_mesh_compression_enable=True,
                                export_draco_mesh_compression_level=DRACO_COMPRESS_LEVEL,
                                export_draco_position_quantization=DRACO_QUANTIZATION_SETTINGS[0], 
                                export_draco_normal_quantization=DRACO_QUANTIZATION_SETTINGS[1],
                                export_draco_texcoord_quantization=DRACO_QUANTIZATION_SETTINGS[2],
                                export_draco_generic_quantization=DRACO_QUANTIZATION_SETTINGS[3])

#converts .stl files to .glb.
def convert_stl(file_path, output_path):
    empty_blender_scene()
    bpy.ops.wm.stl_import(filepath=file_path)
    bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB', export_materials='EXPORT', export_normals=True,
                              export_draco_mesh_compression_enable=True,
                                export_draco_mesh_compression_level=DRACO_COMPRESS_LEVEL,
                                export_draco_position_quantization=DRACO_QUANTIZATION_SETTINGS[0], 
                                export_draco_normal_quantization=DRACO_QUANTIZATION_SETTINGS[1],
                                export_draco_texcoord_quantization=DRACO_QUANTIZATION_SETTINGS[2],
                                export_draco_generic_quantization=DRACO_QUANTIZATION_SETTINGS[3])

def convert_non_cad(file_path, file_type):
    try:
        output_path = os.environ.get("OUTPUT_PATH")
        if file_type == ".obj":
            convert_obj(file_path, output_path)
        elif file_type == ".fbx":
            convert_fbx(file_path, output_path)
        elif file_type == ".stl":
            convert_stl(file_path, output_path)
        else:
            print("Error: Unsupported 3D model type!")
    finally:
        empty_blender_scene()
