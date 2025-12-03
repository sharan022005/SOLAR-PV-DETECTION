import os
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
from .utils import sqft_to_radius_meters, download_maptiler_static_sat

# Find the project root by going up from current file
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Set MAPTILER_API_KEY via environment variable
MAPTILER_API_KEY = os.environ.get("MAPTILER_API_KEY", "YOUR_MAPTILER_API_KEY")

if MAPTILER_API_KEY == "YOUR_MAPTILER_API_KEY":
    print("[WARNING] MAPTILER_API_KEY not found in environment. Using default placeholder.")
    print(f"[INFO] Checked for .env at: {env_path}")

def fetch_for_coordinate(lat, lon, buffer_sqft=1200, size=640):
    """
    Fetch satellite image for given lat/lon with buffer radius.
    Returns: PIL.Image, image_metadata (dict), radius_meters
    """
    radius_m = sqft_to_radius_meters(buffer_sqft)
    img, metadata = download_maptiler_static_sat(lat, lon, radius_m, MAPTILER_API_KEY, size=size)
    metadata.update({"capture_date": None})
    return img, metadata, radius_m
