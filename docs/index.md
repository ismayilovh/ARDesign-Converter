# ARDesign Converter

ARDesign Converter turns supported 3D model files into GLB assets with Draco mesh compression. The ARDesign Server launches the converter in an isolated Docker container for each conversion job.

## Guides

| Guide | Contents |
|---|---|
| [Overview](overview.md) | Formats, output, and command-line usage |
| [Architecture](architecture.md) | Import paths, scaling, and compression flow |
| [Deployment](deployment.md) | Docker image build, manual runs, and server integration |
| [Maintenance](maintenance.md) | Pinned toolchain and conversion constraints |
| [API reference](api/pipeline.md) | Generated reference for the current Python modules |

## Quick reference

```bash
python main.py <input_model_path> [mm|cm|in|m]
```

The command writes `output.glb` by default. Set `OUTPUT_PATH` to select another destination. Run the command inside the converter's configured Python environment; CAD formats also require the FreeCAD runtime and a display server such as `xvfb-run`.

For the complete container workflow, see [Deployment](deployment.md). For API hosting and image rollout, see the [ARDesign Server documentation](https://ismayilovh.github.io/ARDesign-Server/).
