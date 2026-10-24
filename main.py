
import os
import shutil
import sys
from utils import convert_file_to_glb


def main(args):
    if len(args) not in (1, 2):
        print("Usage: main.py <input_model_path> [mm|cm|in|m]", file=sys.stderr)
        return 2

    input_file_path = os.path.abspath(args[0])
    scale = args[1].lower() if len(args) == 2 else "m"
    if scale not in {"mm", "cm", "in", "m"}:
        print(f"Unsupported scale '{args[1]}'; expected mm, cm, in, or m.", file=sys.stderr)
        return 2

    # ARDesign Server invokes the converter from /app/converter and collects
    # OUTPUT_PATH from the job's output directory.
    legacy_output_path = os.path.abspath("out.glb")
    output_path = os.path.abspath(os.environ.get("OUTPUT_PATH", "output.glb"))
    os.environ["OUTPUT_PATH"] = output_path
    os.environ["MODEL_SCALE"] = scale

    try:
        convert_file_to_glb(input_file_path, scale)
        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"Conversion did not produce a non-empty GLB at {output_path}")
        # Keep the original one-argument CLI's out.glb artifact for existing
        # callers while providing output.glb for the ARDesign Server contract.
        if "OUTPUT_PATH" not in os.environ and output_path != legacy_output_path:
            shutil.copyfile(output_path, legacy_output_path)
    except Exception as exc:
        print(f"Conversion failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    try:
        exit_code = main(sys.argv[1:])
    except SystemExit as exc:
        # The dispatcher can call sys.exit() on conversion errors.
        exit_code = exc.code if isinstance(exc.code, int) else 1

    cad_extensions = {".iges", ".igs", ".stp", ".step"}
    is_cad_input = (
        len(sys.argv) > 1
        and os.path.splitext(sys.argv[1])[1].lower() in cad_extensions
    )
    if is_cad_input:
        # FreeCAD/Qt native teardown can hang after the GLB has been written.
        # This process handles one model and runs in a disposable container, so
        # flush diagnostics and let the OS release native resources on exit.
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass
        os._exit(exit_code)

    sys.exit(exit_code)
