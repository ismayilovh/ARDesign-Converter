import os
import sys
import bpy
sys.path.append("/usr/local/lib")

from convert_cad_formats import convert_cad
from convert_non_cad_formats import (
    apply_draco_compression,
    convert_non_cad,
    unit_to_meters,
)

CAD_FILE_LIST = [".iges", ".igs", ".stp", ".step"]
NONCAD_FILE_LIST = [".obj", ".stl", ".fbx", ".glb", ".gltf"]

#converts a single file
def convert_file_to_glb(abs_input_file_path, scale="m"):

    ext = (os.path.splitext(abs_input_file_path)[1]).lower()
    scale_factor = unit_to_meters(scale)
    try:
        if (ext in NONCAD_FILE_LIST):
            convert_non_cad(abs_input_file_path, ext, scale_factor)
            print("Conversion to .glb using bpy successful.")
        elif (ext in CAD_FILE_LIST):
            os.environ["MODEL_PATH"] = abs_input_file_path 
            convert_cad()
            apply_draco_compression(os.environ["OUTPUT_PATH"], scale_factor)
            print("Conversion to .glb with FreeCAD successful.")
        else:
            raise ValueError(f"Unsupported 3D model format: {ext or '(no extension)'}")
    except Exception as e:
        print(f"An Error Occured: {str(e)}")
        sys.exit(1)

