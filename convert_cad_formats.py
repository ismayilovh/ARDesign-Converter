import FreeCAD
import FreeCADGui
import os

MACRO_SCRIPT_NAME = "freecad_converter.py"
def convert_cad():

    #start gui
    FreeCADGui.showMainWindow()

    macro_script_path = os.path.abspath(MACRO_SCRIPT_NAME)
    macro_name = FreeCADGui.Command.createCustomCommand(macro_script_path)

    FreeCADGui.runCommand(macro_name)