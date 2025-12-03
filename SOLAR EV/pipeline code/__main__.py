from .inference import run_inference_on_excel
from .test_single_coordinate import test_single_coordinate

# Usage: 
#   from pipeline_code import run_inference_on_excel, test_single_coordinate
#   run_inference_on_excel("input.csv", "solar_model.pt", "predictions")

# No main function or CLI interface needed as the module now exposes functions for import
