# Deployment

The Docker image builds its own Blender and FreeCAD toolchains. It is a Linux image and requires a lengthy native build with network access to the upstream source repositories and package mirrors.

## Build the image

From the repository root:

```bash
docker build --build-arg BUILD_JOBS=2 -t ismayilovh/ardesign-converter:dev .
```

`BUILD_JOBS` controls parallel native compilation. Increase it only when the builder has enough memory. The `Dockerfile` pins Blender to 4.5.3 and FreeCAD to 1.0.0, installs the Blender Python wheel in a Python 3.11 virtual environment, and runs the image under `xvfb-run` for FreeCAD's GUI APIs.

## Run the bundled conversion checks

The image's default entrypoint runs `test.py` against the model files copied into `test_models/`:

```bash
docker run --rm ismayilovh/ardesign-converter:dev
```

These checks need the full converter image; they are not ordinary host Python unit tests.

## Convert one model in Docker

Mount an input and output directory and override the image entrypoint so the container runs `main.py` instead of the bundled test runner:

```bash
mkdir -p output
docker run --rm \
  --entrypoint /usr/bin/xvfb-run \
  -e OUTPUT_PATH=/output/output.glb \
  -v "$PWD/test_models:/input:ro" \
  -v "$PWD/output:/output" \
  ismayilovh/ardesign-converter:dev \
  -a /app/converter/venv/bin/python3.11 /app/converter/main.py \
  "/input/living room (obj)/living_room.obj" mm
```

The example keeps source models read-only and writes the GLB to the mounted output directory. Use `xvfb-run` for all formats because the CAD path starts FreeCAD GUI APIs, even though the job is headless.

## ARDesign Server integration

The server worker pulls the converter image configured by `CONVERTER_IMAGE`, starts an ephemeral container for a conversion job, copies input and output files through Docker, and removes the container afterward. The default published image is `ismayilovh/ardesign-converter:latest`; pin a version tag for a deployment. Follow the [ARDesign Server runbook](https://github.com/ismayilovh/ARDesign-Server/blob/master/fastapi_app/README.md) when rolling out a new converter image.
