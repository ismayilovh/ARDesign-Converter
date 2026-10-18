# ARDesign Converter

ARDesign Converter converts 3D model files into compressed GLB files for use by ARDesign clients. It combines Blender's Python module (`bpy`) with FreeCAD for CAD imports.

- **Documentation:** [ARDesign Converter docs](https://ismayilovh.github.io/ARDesign-Converter/)
- **Server integration:** [ARDesign Server docs](https://ismayilovh.github.io/ARDesign-Server/)
- **Supported formats, architecture, deployment, maintenance, and API:** see the [documentation source](docs/index.md).

The production image is built from `Dockerfile`. It compiles Blender 4.5.3 and FreeCAD 1.0.0, and its default entrypoint runs the bundled conversion smoke cases. ARDesign Server overrides the container command to convert one submitted model per container.
