
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
    sys.exit(main(sys.argv[1:]))
