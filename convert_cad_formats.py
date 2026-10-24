import FreeCAD
import FreeCADGui
import os


def convert_cad():
    # Start the GUI APIs needed by ImportGui, even in the headless Xvfb job.
    FreeCADGui.showMainWindow()

    # Resolve the macro beside this module rather than relative to CWD. The
    # ARDesign Server runs the converter with CWD=/tmp/work so output.glb is
    # collected from there.
    os.environ.pop("CAD_CONVERSION_ERROR", None)
    macro_script_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "freecad_converter.py"
    )
    macro_name = FreeCADGui.Command.createCustomCommand(macro_script_path)
    FreeCADGui.runCommand(macro_name)

    # FreeCAD's command runner can report a macro exception without raising it
    # in this Python caller. The macro records failures in this process's env.
    error = os.environ.pop("CAD_CONVERSION_ERROR", None)
    if error:
        raise RuntimeError(f"FreeCAD CAD import/export failed: {error}")
