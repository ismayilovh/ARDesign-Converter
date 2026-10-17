import FreeCAD
import FreeCADGui
import os

def convert_cad():

    #start gui
    FreeCADGui.showMainWindow()

    # Resolve the macro beside this module rather than relative to CWD. The
    # ARPatent worker runs the converter with CWD=/tmp/work so output.glb is
    # collected from there.
    macro_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "freecad_converter.py")
    macro_name = FreeCADGui.Command.createCustomCommand(macro_script_path)

    FreeCADGui.runCommand(macro_name)
