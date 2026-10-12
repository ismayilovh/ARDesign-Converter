
import sys
import os
from utils import convert_file_to_glb

input_file_path = sys.argv[1]
os.environ["OUTPUT_PATH"] = "out.glb"
convert_file_to_glb(input_file_path)