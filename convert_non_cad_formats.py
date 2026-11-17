import bpy
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

DRACO_COMPRESS_LEVEL = 6
DRACO_QUANTIZATION_SETTINGS = (16, 12, 20, 12)
UNIT_TO_METERS = {"mm": 0.001, "cm": 0.01, "in": 0.0254, "m": 1.0}
ILLUM_ZERO = re.compile(r"(?mi)^(\s*illum\s+)0(?=\s*(?:#.*)?$)")


def unit_to_meters(unit):
    try:
        return UNIT_TO_METERS[unit.lower()]
    except (AttributeError, KeyError):
        raise ValueError(f"Unsupported scale unit '{unit}'; expected mm, cm, in, or m")


def _scale_imported_model(scale_factor):
    """Scale only hierarchy roots so parented model parts are not scaled twice."""
    if scale_factor == 1.0:
        return
    for obj in bpy.context.scene.objects:
        if obj.parent is None:
            obj.scale = tuple(component * scale_factor for component in obj.scale)


def _link_or_copy(source, destination):
    """Populate an isolated import tree without mutating the uploaded files."""
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


@contextmanager
def _obj_import_path_with_supported_illum(file_path):
    """Yield an OBJ path with unsupported ``illum 0`` values normalised.

    Blender's OBJ importer emits a warning for ``illum 0`` although its
    resulting Principled material is the same non-reflective approximation it
    uses for ``illum 1``. Attempt in-place temporary normalisation if the MTL
    files are writable (restoring them on exit). If read-only, stage a minimal
    isolated copy with the modified MTL declarations without recursively
    walking parent directories (e.g. /tmp).
    """
    source_obj = Path(file_path).resolve()
    source_root = source_obj.parent

    # Find MTL files referenced by the OBJ or beside it in the same directory
    mtl_files = []
    mtllib_re = re.compile(r"^\s*mtllib\s+(.+)$", re.IGNORECASE)
    try:
        with open(source_obj, "r", encoding="utf-8", errors="surrogateescape") as stream:
            for line in stream:
                match = mtllib_re.match(line)
                if match:
                    candidate = source_root / match.group(1).strip()
                    if candidate.is_file() and candidate not in mtl_files:
                        mtl_files.append(candidate)
    except OSError:
        pass

    if not mtl_files:
        try:
            mtl_files = [p for p in source_root.iterdir()
                         if p.is_file() and p.suffix.lower() == ".mtl"]
        except OSError:
            pass

    replacements = {}
    replacement_count = 0
    for mtl_path in mtl_files:
        try:
            contents = mtl_path.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            continue
        sanitized, count = ILLUM_ZERO.subn(r"\g<1>1", contents)
        if count:
            replacements[mtl_path] = (contents, sanitized)
            replacement_count += count

    if not replacements:
        yield str(source_obj)
        return

    # Strategy 1: Attempt in-place temporary modification with restoration in finally
    can_modify_in_place = True
    for mtl_path, (original, sanitized) in replacements.items():
        try:
            mtl_path.write_text(sanitized, encoding="utf-8", errors="surrogateescape")
        except OSError:
            can_modify_in_place = False
            # Revert any already written
            for p, (orig, _) in replacements.items():
                if p == mtl_path:
                    break
                try:
                    p.write_text(orig, encoding="utf-8", errors="surrogateescape")
                except OSError:
                    pass
            break

    if can_modify_in_place:
        print(
            f"ARDesign: normalized {replacement_count} unsupported OBJ illum 0 "
            "declaration(s) to illum 1 in-place.",
            flush=True,
        )
        try:
            yield str(source_obj)
        finally:
            for mtl_path, (original, _) in replacements.items():
                try:
                    mtl_path.write_text(original, encoding="utf-8", errors="surrogateescape")
                except OSError:
                    pass
        return

    # Strategy 2: If read-only, stage a minimal bundle in a temp folder
    try:
        temporary = tempfile.mkdtemp(prefix="ardesign-obj-")
    except OSError as exc:
        print(
            "ARDesign: could not create an isolated OBJ staging area for illum 0 "
            f"normalization ({exc}); importing the original file.",
            flush=True,
        )
        yield str(source_obj)
        return

    try:
        staged_root = Path(temporary) / "bundle"
        staged_root.mkdir(parents=True, exist_ok=True)
        try:
            # Stage only direct files in source_root (avoid traversing nested folders in /tmp)
            for path in source_root.iterdir():
                if path.is_file():
                    staged_path = staged_root / path.name
                    if path in replacements:
                        staged_path.write_text(
                            replacements[path][1], encoding="utf-8", errors="surrogateescape"
                        )
                    else:
                        _link_or_copy(path, staged_path)
        except OSError as exc:
            print(
                "ARDesign: could not stage OBJ materials for illum 0 normalization "
                f"({exc}); importing the original file.",
                flush=True,
            )
            yield str(source_obj)
            return

        print(
            "ARDesign: normalized "
            f"{replacement_count} unsupported OBJ illum 0 declaration(s) to illum 1 "
            "in an isolated import copy.",
            flush=True,
        )
        yield str(staged_root / source_obj.name)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def _linked_image_nodes(socket):
    """Yield image texture nodes connected upstream of a shader socket."""
    seen = set()

    def visit(current_socket):
        for link in current_socket.links:
            node = link.from_node
            pointer = node.as_pointer()
            if pointer in seen:
                continue
            seen.add(pointer)
            if node.type == "TEX_IMAGE":
                yield node
                continue
            for input_socket in node.inputs:
                if input_socket.is_linked:
                    yield from visit(input_socket)

    yield from visit(socket)


SAMPLER_PROPERTIES = ("interpolation", "extension", "projection", "projection_blend")


def _socket_default_signature(socket):
    """Return a stable representation of an unlinked texture-vector input."""
    value = socket.default_value
    try:
        return tuple(round(float(component), 9) for component in value)
    except TypeError:
        return round(float(value), 9)


def _texture_vector_socket_signature(vector, seen=None):
    """Describe the portion of a vector-node graph relevant to glTF mapping."""
    if vector is None:
        return None
    if not vector.is_linked:
        return ("constant", _socket_default_signature(vector))

    seen = set() if seen is None else seen
    link = vector.links[0]
    node = link.from_node
    pointer = node.as_pointer()
    if pointer in seen:
        return ("cycle", node.type)
    seen.add(pointer)

    if node.type == "TEX_COORD":
        return ("texcoord", link.from_socket.name)
    if node.type == "UVMAP":
        return ("uvmap", node.uv_map)
    if node.type == "MAPPING":
        input_socket = node.inputs.get("Vector")
        upstream = (
            _texture_vector_socket_signature(input_socket, seen)
            if input_socket is not None else None
        )
        return (
            "mapping",
            node.vector_type,
            _socket_default_signature(node.inputs["Location"]),
            _socket_default_signature(node.inputs["Rotation"]),
            _socket_default_signature(node.inputs["Scale"]),
            upstream,
        )
    if node.type == "REROUTE":
        return _texture_vector_socket_signature(node.inputs[0], seen)

    # A pointer is intentionally used only for graph types we cannot prove
    # equivalent.  That keeps the exporter warning for procedural mappings
    # which would need baking to be represented faithfully in glTF.
    return ("unsupported", node.type, pointer, link.from_socket.identifier)


def _image_vector_signature(image_node):
    return _texture_vector_socket_signature(image_node.inputs.get("Vector"))


def _image_texture_sampling_signature(image_node):
    """Return the sampler and texture-coordinate state glTF must share."""
    return (
        *(getattr(image_node, prop, None) for prop in SAMPLER_PROPERTIES),
        _image_vector_signature(image_node),
    )


def _patch_gltf_texture_exporter():
    """Correct Blender's packing of separate Base Color and alpha images.

    Blender's glTF exporter obtains pixel values from a colour image in linear
    space.  Its ``__encode_unhappy`` path is used when it has to combine that
    image with a separate alpha image, then writes those linear values directly
    to the generated PNG.  glTF Base Color RGB is sRGB, so this makes colours
    visibly too dark (the Dutch ship sails are a representative example).

    The previous hook ran after ``gather_image`` returned.  That is too late:
    gathering encodes the PNG before returning.  Patch the encode method and
    the exact packing branch instead, and only for an sRGB RGB image combined
    with a different alpha image.  Data textures (normal, metallic and
    roughness) are left untouched.
    """
    import numpy as np
    from io_scene_gltf2.blender.exp.material.encode_image import (
        Channel,
        ExportImage,
        FillImage,
        FillImageRGB2BW,
        FillWith,
        FillWhite,
        TmpImageGuard,
        make_temp_image_copy,
    )

    if getattr(ExportImage, "_ardesign_texture_exporter_patched", False):
        print("ARDesign texture-export hook is active.", flush=True)
        return

    original_encode = ExportImage.encode
    original_encode_unhappy = ExportImage._ExportImage__encode_unhappy
    original_encode_numpy = ExportImage._ExportImage__encode_from_numpy_array

    def needs_srgb_basecolor_packing(export_image):
        """Return true only for RGB-from-colour + alpha-from-other-image."""
        fills = export_image.fills
        rgb_fills = [fills.get(Channel.R), fills.get(Channel.G), fills.get(Channel.B)]
        alpha_fill = fills.get(Channel.A)

        if not all(isinstance(fill, FillImage) for fill in rgb_fills):
            return False

        # Verify all three color channels originate from the same image and 0, 1, 2
        rgb_images = {fill.image for fill in rgb_fills}
        if len(rgb_images) != 1:
            return False

        if [int(fill.src_chan) for fill in rgb_fills] != [0, 1, 2]:
            return False

        rgb_image = next(iter(rgb_images))
        if isinstance(alpha_fill, (FillImage, FillImageRGB2BW)) and alpha_fill.image == rgb_image:
            return False

        if alpha_fill is not None and not isinstance(alpha_fill, (FillImage, FillImageRGB2BW, FillWith, FillWhite)):
            return False

        color_space = getattr(rgb_image.colorspace_settings, "name", "").casefold()
        if color_space in ("non-color", "raw"):
            return False

        return True

    def encode_with_srgb_detection(self, mime_type, export_settings):
        self._ardesign_srgb_basecolor_packing = needs_srgb_basecolor_packing(self)
        if self._ardesign_srgb_basecolor_packing:
            rgb_image = self.fills[Channel.R].image
            alpha_image = getattr(self.fills[Channel.A], "image", None)
            print(
                "ARDesign: packing an sRGB Base Color image with a separate "
                f"alpha value ({rgb_image.name} + "
                f"{getattr(alpha_image, 'name', type(self.fills.get(Channel.A)).__name__)}).",
                flush=True,
            )
        return original_encode(self, mime_type, export_settings)

    def encode_unhappy_with_srgb_rgb(self, export_settings):
        if not getattr(self, "_ardesign_srgb_basecolor_packing", False):
            return original_encode_unhappy(self, export_settings)

        # This follows Blender 4.5.3's __encode_unhappy implementation.  The
        # single deliberate difference is converting the composed RGB values
        # from Blender's linear floats to sRGB before the generated PNG is
        # saved.  Alpha remains linear as glTF requires.
        images = []
        for fill in self.fills.values():
            if isinstance(fill, (FillImage, FillImageRGB2BW)) and fill.image not in images:
                images.append(fill.image)
                export_settings["exported_images"][fill.image.name] = 2

        if not images:
            return original_encode_unhappy(self, export_settings)

        width = max(image.size[0] for image in images)
        height = max(image.size[1] for image in images)
        out_buf = np.ones(width * height * 4, np.float32)
        tmp_buf = np.empty(width * height * 4, np.float32)

        for image in images:
            if image.size[0] == width and image.size[1] == height:
                image.pixels.foreach_get(tmp_buf)
            else:
                with TmpImageGuard() as guard:
                    make_temp_image_copy(guard, src_image=image)
                    tmp_image = guard.image
                    tmp_image.scale(width, height)
                    tmp_image.pixels.foreach_get(tmp_buf)

            for dst_chan, fill in self.fills.items():
                if isinstance(fill, FillImage) and fill.image == image:
                    out_buf[int(dst_chan)::4] = tmp_buf[int(fill.src_chan)::4]
                elif isinstance(fill, FillImageRGB2BW) and fill.image == image:
                    out_buf[int(dst_chan)::4] = (
                        tmp_buf[0::4] * 0.2989
                        + tmp_buf[1::4] * 0.5870
                        + tmp_buf[2::4] * 0.1140
                    )
                    if image.alpha_mode in {"STRAIGHT", "PREMUL"}:
                        out_buf[int(dst_chan)::4] *= tmp_buf[3::4]

        # Apply constant fills (FillWith, FillWhite)
        for dst_chan, fill in self.fills.items():
            if isinstance(fill, (FillWith, FillWhite)):
                out_buf[int(dst_chan)::4] = getattr(fill, "value", 1.0)

        linear_rgb = np.clip(out_buf.reshape((-1, 4))[:, :3], 0.0, 1.0)
        out_buf.reshape((-1, 4))[:, :3] = np.where(
            linear_rgb <= 0.0031308,
            linear_rgb * 12.92,
            1.055 * np.power(linear_rgb, 1.0 / 2.4) - 0.055,
        )
        print(
            "ARDesign: wrote packed Base Color RGB as sRGB; alpha channel preserved.",
            flush=True,
        )
        return original_encode_numpy(self, out_buf, (width, height), export_settings)

    ExportImage.encode = encode_with_srgb_detection
    ExportImage._ExportImage__encode_unhappy = encode_unhappy_with_srgb_rgb
    ExportImage._ardesign_texture_exporter_patched = True
    print("Installed ARDesign Base Color/alpha texture-packing fix.", flush=True)

def _normalize_glb_texture_samplers():
    """Align samplers for channels glTF must store in one texture.

    glTF has one sampler for the combined base-color/alpha texture and one
    sampler for the combined metallic/roughness texture. Blender's exporter
    chooses the first image node's sampler when these channels use different
    image nodes. Use the primary channel's sampler consistently so the result
    does not depend on node traversal order.
    """
    channel_groups = (
        ("Base Color", "Alpha"),
        ("Metallic", "Roughness"),
        ("Roughness", "Metallic"),
    )

    for material in bpy.data.materials:
        if not material.use_nodes or material.node_tree is None:
            continue
        for shader in material.node_tree.nodes:
            if shader.type != "BSDF_PRINCIPLED":
                continue
            for primary_name, companion_name in channel_groups:
                primary_socket = shader.inputs.get(primary_name)
                companion_socket = shader.inputs.get(companion_name)
                if primary_socket is None or companion_socket is None:
                    continue
                primary_nodes = list(_linked_image_nodes(primary_socket))
                if not primary_nodes:
                    continue
                reference = primary_nodes[0]
                for image_node in _linked_image_nodes(companion_socket):
                    if image_node == reference:
                        continue
                    if _image_vector_signature(image_node) != _image_vector_signature(reference):
                        print(
                            f"ARDesign: {material.name} uses different texture-coordinate "
                            f"mappings for {primary_name} and {companion_name}; preserving "
                            "Blender's warning because faithful GLB output requires baking.",
                            flush=True,
                        )
                        continue
                    changed = []
                    for prop in SAMPLER_PROPERTIES:
                        if hasattr(reference, prop) and hasattr(image_node, prop):
                            value = getattr(reference, prop)
                            if getattr(image_node, prop) != value:
                                setattr(image_node, prop, value)
                                changed.append(prop)
                    if changed:
                        print(
                            f"Normalized {material.name} {companion_name} texture sampler "
                            f"to match {primary_name} ({', '.join(changed)}).",
                            flush=True,
                        )


def _patch_gltf_sampler_warning():
    """Suppress Blender's multi-node sampler warning only when it is harmless.

    Base Color and alpha commonly originate from two Image Texture nodes.  glTF
    correctly has one sampler for the packed image, and the normalisation above
    makes its filter/wrap settings identical.  Blender nevertheless emits its
    generic warning solely because two nodes exist.  Keep the warning when the
    UV source or sampler settings differ, because such a material cannot be
    represented by one glTF texture without baking; suppress it only when the
    two nodes are demonstrably equivalent.
    """
    from io_scene_gltf2.blender.exp.material import texture as gltf_texture
    from io_scene_gltf2.blender.exp.material.search_node_tree import get_texture_node_from_socket

    if getattr(gltf_texture, "_ardesign_sampler_warning_patched", False):
        return

    original_gather_sampler = gltf_texture.__dict__["__gather_sampler"]
    warning_text = "More than one shader node tex image used for a texture."

    def nodes_share_a_sampler(shader_nodes):
        reference_signature = _image_texture_sampling_signature(
            shader_nodes[0].shader_node
        )
        for result in shader_nodes[1:]:
            candidate_signature = _image_texture_sampling_signature(result.shader_node)
            if candidate_signature != reference_signature:
                return False
        return True

    def gather_sampler_without_false_warning(blender_shader_sockets, export_settings):
        shader_nodes = [
            get_texture_node_from_socket(socket, export_settings)
            for socket in blender_shader_sockets
        ]
        shader_nodes = [node for node in shader_nodes if node is not None]
        if len(shader_nodes) < 2 or not nodes_share_a_sampler(shader_nodes):
            return original_gather_sampler(blender_shader_sockets, export_settings)

        logger = export_settings.get("log")
        original_warning = getattr(logger, "warning", None)
        if original_warning is None:
            return original_gather_sampler(blender_shader_sockets, export_settings)

        suppressed = False

        def warning_without_false_positive(message, *args, **kwargs):
            nonlocal suppressed
            if str(message).startswith(warning_text):
                suppressed = True
                return None
            return original_warning(message, *args, **kwargs)

        try:
            logger.warning = warning_without_false_positive
        except (AttributeError, TypeError):
            return original_gather_sampler(blender_shader_sockets, export_settings)
        try:
            result = original_gather_sampler(blender_shader_sockets, export_settings)
        finally:
            try:
                logger.warning = original_warning
            except (AttributeError, TypeError):
                pass

        if suppressed:
            print(
                "ARDesign: combined texture nodes share one sampler and UV source; "
                "suppressed Blender's redundant sampler warning.",
                flush=True,
            )
        return result

    gltf_texture.__dict__["__gather_sampler"] = gather_sampler_without_false_warning
    gltf_texture._ardesign_sampler_warning_patched = True


def _export_glb(output_path):
    _patch_gltf_texture_exporter()
    _normalize_glb_texture_samplers()
    _patch_gltf_sampler_warning()
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        export_materials='EXPORT',
        export_normals=True,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=DRACO_COMPRESS_LEVEL,
        export_draco_position_quantization=DRACO_QUANTIZATION_SETTINGS[0],
        export_draco_normal_quantization=DRACO_QUANTIZATION_SETTINGS[1],
        export_draco_texcoord_quantization=DRACO_QUANTIZATION_SETTINGS[2],
        export_draco_generic_quantization=DRACO_QUANTIZATION_SETTINGS[3],
    )

#empty scene to prevent loading old stuff.
def empty_blender_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def apply_draco_compression(output_path, scale_factor=1.0):
    empty_blender_scene()
    try:
        bpy.ops.import_scene.gltf(filepath=output_path)
    except Exception as exc:
        raise RuntimeError(
            f"Blender could not import FreeCAD's intermediate GLB '{output_path}': {exc}"
        ) from exc

    meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.data is not None and len(obj.data.polygons) > 0
    ]
    if not meshes:
        raise RuntimeError(
            f"FreeCAD's intermediate GLB '{output_path}' contains no mesh geometry; "
            "the CAD import/export produced an empty scene"
        )

    _scale_imported_model(scale_factor)
    _export_glb(output_path)

#converts .obj files to .glb.
def convert_obj(file_path, output_path, scale_factor=1.0):
    empty_blender_scene()
    with _obj_import_path_with_supported_illum(file_path) as import_path:
        bpy.ops.wm.obj_import(filepath=import_path)
    _scale_imported_model(scale_factor)
    _export_glb(output_path)


#converts .fbx files to .glb.
def convert_fbx(file_path, output_path, scale_factor=1.0):
    empty_blender_scene()
    bpy.ops.wm.fbx_import(filepath=file_path)
    _scale_imported_model(scale_factor)
    _export_glb(output_path)

#converts .stl files to .glb.
def convert_stl(file_path, output_path, scale_factor=1.0):
    empty_blender_scene()
    bpy.ops.wm.stl_import(filepath=file_path)
    _scale_imported_model(scale_factor)
    _export_glb(output_path)

def process_glb_gltf(file_path, output_path):
    empty_blender_scene()
    bpy.ops.import_scene.gltf(filepath=file_path)
    # Existing GLB/GLTF coordinates are already authored in meters. Re-export
    # for consistent Draco compression without applying the input-unit scale.
    _export_glb(output_path)


def convert_non_cad(file_path, file_type, scale_factor=1.0):
    try:
        output_path = os.environ.get("OUTPUT_PATH")
        if not output_path:
            raise RuntimeError("OUTPUT_PATH is not configured")
        if file_type == ".obj":
            convert_obj(file_path, output_path, scale_factor)
        elif file_type == ".fbx":
            convert_fbx(file_path, output_path, scale_factor)
        elif file_type == ".stl":
            convert_stl(file_path, output_path, scale_factor)
        elif file_type in (".glb", ".gltf"):
            process_glb_gltf(file_path, output_path)
        else:
            raise ValueError(f"Unsupported 3D model type: {file_type}")
    finally:
        empty_blender_scene()
