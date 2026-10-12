import os
import sys
import bpy
sys.path.append("/usr/local/lib")

from convert_cad_formats import convert_cad
from convert_non_cad_formats import convert_non_cad, apply_draco_compression

CAD_FILE_LIST = [".iges", ".igs", ".stp", ".step"]
NONCAD_FILE_LIST = [".obj", ".stl", ".fbx"]

#converts a single file
def convert_file_to_glb(abs_input_file_path):

    ext = (os.path.splitext(abs_input_file_path)[1]).lower()
    try:
        if (ext in NONCAD_FILE_LIST):
            convert_non_cad(abs_input_file_path, ext)
            print("Conversion to .glb using bpy successful.")
        elif (ext in CAD_FILE_LIST):
            os.environ["MODEL_PATH"] = abs_input_file_path 
            convert_cad()
            apply_draco_compression(os.environ["OUTPUT_PATH"])
            print("Conversion to .glb with FreeCAD successful.")
        else:
            print("Unsupported 3D model path!")
    except Exception as e:
        print(f"An Error Occured: {str(e)}")
        sys.exit(1)

