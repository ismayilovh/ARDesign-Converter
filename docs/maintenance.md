# Maintenance

## Keep toolchain versions aligned

The `Dockerfile` pins Blender to 4.5.3 and FreeCAD to 1.0.0. Changing either version can affect import operators, GLTF export properties, native dependencies, and the produced GLB. Build and exercise the complete container before publishing a changed toolchain.

## Keep output configuration consistent

`main.py` sets `OUTPUT_PATH` and `MODEL_SCALE`; CAD import also uses `MODEL_PATH`. The server worker expects the output at the path it configures and copies. Keep the command arguments, environment variables, and worker collection logic aligned when changing the CLI.

## Preserve one shared GLB export path

Imported formats use Blender's GLB exporter with Draco compression. GLB and GLTF inputs are re-exported so they receive the same compression settings. Keep format-specific preprocessing separate from the final output path unless a format requires different semantics.

## Scaling rules

The converter scales root objects so parented mesh parts are not transformed twice. GLB and GLTF inputs preserve their authored meter coordinates; other supported formats use the selected `mm`, `cm`, `in`, or `m` scale. Do not silently apply the scale parameter to native GLB/GLTF without changing that contract.

## FreeCAD needs a virtual display

FreeCAD's import code uses `FreeCADGui` and `ImportGui`, so it runs under `xvfb-run` in the Linux container. STEP and IGES conversion is not supported by a plain host Python installation without the matching FreeCAD runtime and display setup.

## Test in the production image

Blender's `bpy` wheel and FreeCAD are built specifically for the container. Host Python checks cannot validate those native integrations. Run the bundled container checks and representative model conversions before publishing a new image tag.
