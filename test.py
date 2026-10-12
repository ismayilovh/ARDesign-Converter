#Code to test converter system
from utils import convert_file_to_glb, CAD_FILE_LIST, NONCAD_FILE_LIST
import os


def run_test_cases():
    test_file_folder = "test_models"
    test_output_folder = "test_outputs"
    
    print("Running test cases...")

    walk = os.walk(test_file_folder)
    count = len(next(walk)[1])
    curr = 1

    os.makedirs(test_output_folder,exist_ok=True)

    try:
        for root, _, files in walk:    
            for file in files:
                name, ext = os.path.splitext(file)
                if (ext in CAD_FILE_LIST or ext in NONCAD_FILE_LIST):
                    print(f"Running test case {curr}/{count}:")
                    abspath = os.path.abspath(os.path.join(root, file))
                    os.environ["OUTPUT_PATH"] = f"{test_output_folder}/{name}_out.glb"
                    convert_file_to_glb(abspath)
                    curr = curr + 1
        print("All test cases passed!")
    except Exception as e:
        print(f"Test case {curr}/{count} failed with error message: {e}")
    


run_test_cases()
