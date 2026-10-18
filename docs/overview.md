# Overview

The converter accepts one model file and produces a GLB. Blender handles mesh import/export and Draco compression. FreeCAD imports STEP and IGES CAD formats before Blender performs the final compression pass.

## Supported input formats

| Input | Extensions | Import path | Scale handling |
|---|---|---|---|
| Wavefront | `.obj` | Blender (`bpy`) | Converts the requested unit to meters |
| Stereolithography | `.stl` | Blender (`bpy`) | Converts the requested unit to meters |
| Autodesk FBX | `.fbx` | Blender (`bpy`) | Converts the requested unit to meters |
| GL Transmission Format | `.glb`, `.gltf` | Blender (`bpy`) | Preserves authored meter coordinates |
| STEP | `.stp`, `.step` | FreeCAD, then Blender | Converts the requested unit to meters |
| IGES | `.igs`, `.iges` | FreeCAD, then Blender | Converts the requested unit to meters |

Unsupported extensions fail with a non-zero status.

## Command-line interface

```bash
python main.py <input_model_path> [mm|cm|in|m]
```

The scale defaults to meters. `OUTPUT_PATH` can override the output path; otherwise the converter writes `output.glb` in its working directory. In the ARDesign Server container flow, the worker arranges a job-specific output location and copies the resulting GLB out of the short-lived converter container.

The Docker image's default entrypoint runs `test.py`, which iterates the bundled `test_models/` cases. To convert a single model in a container, override that entrypoint; see [Deployment](deployment.md).
