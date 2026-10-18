# FreeCAD bridge

The CAD adapter starts FreeCAD's GUI APIs in the virtual display supplied by `xvfb-run`, imports STEP or IGES files, and exports the imported root objects for Blender's final processing pass. Its executable macro is [`freecad_converter.py`](https://github.com/ismayilovh/ARDesign-Converter/blob/main/freecad_converter.py); the launcher is `convert_cad_formats.convert_cad`.

::: convert_cad_formats
