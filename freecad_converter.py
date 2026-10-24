import os

import FreeCAD
import FreeCADGui  # noqa: F401 - required by ImportGui in the GUI process
import ImportGui  # type: ignore


def _shape_objects(document_objects):
    """Select top-level non-empty shapes, avoiding duplicate child geometry."""
    shape_objects = []
    for obj in document_objects:
        shape = getattr(obj, "Shape", None)
        if shape is not None and not shape.isNull():
            shape_objects.append(obj)

    shape_names = {obj.Name for obj in shape_objects}
    # FreeCAD's InList lists objects that link to an object. If a shape-bearing
    # parent links to another shape-bearing object, export the parent only.
    return [
        obj for obj in shape_objects
        if not any(
            getattr(parent, "Name", None) in shape_names
            for parent in getattr(obj, "InList", ())
        )
    ]


def _describe_objects(document_objects):
    descriptions = []
    for obj in document_objects:
        shape = getattr(obj, "Shape", None)
        shape_state = "no Shape property"
        if shape is not None:
            shape_state = "empty Shape" if shape.isNull() else "non-empty Shape"
        descriptions.append(
            f"{getattr(obj, 'Name', '<unnamed>')} "
            f"({getattr(obj, 'TypeId', type(obj).__name__)}, {shape_state})"
        )
    return descriptions


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

        document_objects = list(doc.Objects)
        export_objects = _shape_objects(document_objects)
        if not export_objects:
            descriptions = _describe_objects(document_objects)
            object_summary = "; ".join(descriptions[:30]) if descriptions else "no document objects"
            if len(descriptions) > 30:
                object_summary += f"; ... and {len(descriptions) - 30} more"
            raise RuntimeError(
                f"FreeCAD imported no non-empty shapes from {model_path}. "
                f"Document objects: {object_summary}"
            )

        print(
            f"FreeCAD imported {len(document_objects)} document object(s), "
            f"selected {len(export_objects)} top-level shape object(s) from "
            f"{os.path.basename(model_path)}; exporting to {output_path}",
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
