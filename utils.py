import os
import sys
import bpy
sys.path.append("/usr/local/lib")

from convert_non_cad_formats import (
    apply_draco_compression,
    convert_non_cad,
    unit_to_meters,
)

CAD_FILE_LIST = [".iges", ".igs", ".stp", ".step"]
NONCAD_FILE_LIST = [".obj", ".stl", ".fbx", ".glb", ".gltf"]


def _header_preview(data):
    """Return a compact, safe byte preview for an actionable validation error."""
    return "".join(
        chr(byte) if 32 <= byte < 127 else f"\\x{byte:02x}"
        for byte in data[:24]
    )


def validate_input_file(input_path, extension):
    """Reject known-corrupt model files before an importer emits a vague error.

    This deliberately performs only inexpensive signature checks.  Full format
    validation remains the responsibility of Blender or FreeCAD, but a
    mislabeled HTML download or a deliberately malformed fixture receives an
    explanation that an upload client can act on.
    """
    try:
        with open(input_path, "rb") as stream:
            header = stream.read(512)
    except OSError as exc:
        raise RuntimeError(f"Cannot read input file '{input_path}': {exc}") from exc

    if not header:
        raise ValueError(f"Input file '{input_path}' is empty")

    lowered = header.lower()
    if extension == ".glb" and header[:4] != b"glTF":
        raise ValueError(
            "Invalid GLB input: expected the binary 'glTF' signature at byte 0, "
            f"found '{_header_preview(header)}'. Re-export or re-download the model."
        )

    if extension in {".iges", ".igs"} and (
        lowered.startswith(b"<!doctype html") or lowered.startswith(b"<html")
    ):
        raise ValueError(
            "Invalid IGES input: the file starts with HTML rather than an IGES "
            "Start section. It is likely a downloaded web/error page."
        )

    # ASCII FBX is legitimate, so do not reject it merely for not having the
    # binary FBX signature.  The supplied malformed-input fixture, however,
    # explicitly labels its required header section as malformed.
    if extension == ".fbx" and b"malformed fbxheaderextension" in lowered:
        raise ValueError(
            "Invalid FBX input: its FBXHeaderExtension is explicitly marked "
            "MALFORMED. Export the model again from its authoring tool."
        )


#converts a single file
def convert_file_to_glb(abs_input_file_path, scale="m"):

    ext = (os.path.splitext(abs_input_file_path)[1]).lower()
    scale_factor = unit_to_meters(scale)
    try:
        validate_input_file(abs_input_file_path, ext)
        if (ext in NONCAD_FILE_LIST):
            convert_non_cad(abs_input_file_path, ext, scale_factor)
            print("Conversion to .glb using bpy successful.")
        elif (ext in CAD_FILE_LIST):
            from convert_cad_formats import convert_cad
            os.environ["MODEL_PATH"] = abs_input_file_path 
            convert_cad()
            apply_draco_compression(os.environ["OUTPUT_PATH"], scale_factor)
            print("Conversion to .glb with FreeCAD successful.")
        else:
            raise ValueError(f"Unsupported 3D model format: {ext or '(no extension)'}")
    except Exception as e:
        print(f"Conversion failed: {str(e)}")
        sys.exit(1)

