import os

import FreeCAD
import FreeCADGui  # noqa: F401 - required by ImportGui in the GUI process
import ImportGui  # type: ignore


def _shape_objects(roots):
    """Flatten FreeCAD containers to non-empty shape objects for export."""
    result = []
    seen = set()
    pending = list(roots)
    while pending:
        obj = pending.pop(0)
        name = getattr(obj, "Name", id(obj))
        if name in seen:
            continue
        seen.add(name)

        shape = getattr(obj, "Shape", None)
        if shape is not None and not shape.isNull():
            result.append(obj)
            continue
        pending.extend(getattr(obj, "Group", ()))
    return result


def convert_step_iges():
    doc = None
    try:
        model_path = os.environ.get("MODEL_PATH")
        output_path = os.environ.get("OUTPUT_PATH")
        if not model_path or not os.path.isfile(model_path):
            raise FileNotFoundError(f"CAD source file is missing: {model_path!r}")
        if not output_path:
            raise RuntimeError("OUTPUT_PATH is not configured")

        doc = FreeCAD.newDocument("ImportScene")
        ImportGui.insert(model_path, doc.Name)
        doc.recompute()

        export_objects = _shape_objects(doc.RootObjects)
        if not export_objects:
            raise RuntimeError(
                f"FreeCAD imported no non-empty shapes from {model_path}; "
                "the STEP/IGES document may contain no supported solid or surface geometry"
            )

        print(
            f"FreeCAD imported {len(export_objects)} shape object(s) "
            f"from {os.path.basename(model_path)}; exporting to {output_path}",
            flush=True,
        )
        ImportGui.export(export_objects, output_path)
        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"FreeCAD produced no non-empty GLB at {output_path}")
    except Exception as exc:
        os.environ["CAD_CONVERSION_ERROR"] = str(exc)
        print(f"FreeCAD CAD import/export failed: {exc}", flush=True)
    finally:
        if doc is not None:
            try:
                FreeCAD.closeDocument(doc.Name)
            except Exception as exc:
                print(f"FreeCAD document cleanup warning: {exc}", flush=True)


convert_step_iges()
