# Solar PV Detection Pipeline

AI-powered pipeline for detecting and quantifying rooftop solar panels using YOLOv8 and satellite imagery.


## Project Structure

\`\`\`
solar-pv-detection/
├── pipeline_code/              # Core inference code
│   ├── __init__.py
│   ├── __main__.py
│   ├── fetch_image.py          # Satellite image retrieval (multi-provider)
│   ├── detect.py               # YOLO inference
│   ├── quantify.py             # Area calculation in m²
│   ├── qc.py                   # Quality control checks
│   ├── inference.py            # End-to-end batch processing
│   ├── utils.py                # Utility functions
│   └── test_single_coordinate.py
├── scripts/
│   └── test_manual.py          # Manual testing script
├── environment/
│   ├── requirements.txt        # Python dependencies (pip)
│   ├── environment.yml         # Conda environment (optional)
│   └── python_version.txt      # Python version: 3.10
├── solar_model.pt              # Trained model weights
├── predictions/                # Inference outputs
│   ├── {sample_id}.json        # Per-site detection results
│   ├── {sample_id}_overlay.png # Visualization with detections
│   └── predictions.json        # Aggregated summary
└── README.md                   # This file
\`\`\`

---

## Development Environment

- **IDE**: Visual Studio Code (VS Code) on Windows
- **Dataset Management**: Google Drive + Google Colab
- **Model Training**: Google Colab (free GPU)
- **Inference**: Local Windows machine

---

## Setup Instructions (Windows + VS Code)

### Prerequisites

- Python 3.10+ installed
- VS Code installed

### Create Virtual Environment

Open VS Code terminal (`Ctrl + `` `) and run:

\`\`\`powershell
# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\activate
\`\`\`

If you get an execution policy error:
\`\`\`powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\activate
\`\`\`

### Install Dependencies

\`\`\`powershell
pip install -r environment/requirements.txt
\`\`\`

### Set MapTiler API Key

Get your free API key at: https://cloud.maptiler.com/account/keys/

**Option A: Create `.env` file** (recommended)
\`\`\`
MAPTILER_API_KEY=your_actual_api_key_here
\`\`\`

**Option B: Set in terminal** (temporary)
\`\`\`powershell
$env:MAPTILER_API_KEY="your_actual_api_key_here"
\`\`\`

---

## Dataset Preparation (Google Drive + Colab)

All dataset management and merging was done using Google Drive and Google Colab.

### Datasets Used

Three Roboflow datasets were combined:
1. Alfred Weber Institute - Roboflow solar panel dataset
2. LSGI547 Project - Roboflow solar panel dataset  
3. Piscinas Y Tenistable - Roboflow solar panel dataset

### How Datasets Were Merged

1. Uploaded 3 Roboflow ZIP files to Google Drive folder: `MyDrive/solar-pv-colab/datasets/`
2. Used Colab notebook to extract and merge datasets
3. Merged dataset saved to: `MyDrive/solar-pv-colab/merged_dataset/`

Final merged structure:
\`\`\`
merged_dataset/
├── images/
│   ├── train/
│   └── val/
├── labels/
│   ├── train/
│   └── val/
└── data.yaml
\`\`\`

---

## Model Training (Google Colab)

Training was performed on Google Colab using free GPU resources.

### Training Configuration

| Parameter | Value |
|-----------|-------|
| Base Model | YOLOv8s (yolov8s.pt) |
| Epochs | 30 |
| Image Size | 640x640 |
| Batch Size | 16 |
| Device | T4 GPU (Colab) |
| Classes | 1 (solar_panel) |

### Training Outputs

- `solar_model.pt` - Final trained weights (in project root)
- `runs/detect/train/results.csv` - Training metrics per epoch
- `runs/detect/train/confusion_matrix.png` - Model performance visualization

---

## Running Inference (Windows + VS Code)

### Option 1: Manual Test (Single Coordinate)

\`\`\`powershell
.\venv\Scripts\activate
python scripts/test_manual.py
\`\`\`

Output in `test_output/`:
\`\`\`
test_output/
├── 1.json            # Detection results
└── 1_overlay.png     # Visualization with bounding boxes
\`\`\`

### Option 2: Batch Inference (Excel Input)

Create input Excel file (`input_sites.xlsx`) with columns:
| sample_id | latitude | longitude |
|-----------|----------|-----------|
| 1 | 40.7128 | -74.0060 |
| 2 | 34.0522 | -118.2437 |
| 3 | 37.7749 | -122.4194 |

Create run script (`run_inference.py`):
\`\`\`python
from pipeline_code.inference import run_inference_on_excel

run_inference_on_excel(
    excel_path='input_sites.xlsx',
    model_path='solar_model.pt',
    output_dir='predictions'
)

print("Inference complete! Check the 'predictions' folder.")
\`\`\`

Run inference:
\`\`\`powershell
.\venv\Scripts\activate
python run_inference.py
\`\`\`

Output in `predictions/`:
\`\`\`
predictions/
├── 1.json
├── 1_overlay.png
├── 2.json
├── 2_overlay.png
├── 3.json
├── 3_overlay.png
└── predictions.json
\`\`\`

---

## Output Format

### JSON Output (Per Site)

\`\`\`json
{
  "sample_id": 1,
  "lat": 40.7128,
  "lon": -74.0060,
  "has_solar": true,
  "confidence": 0.92,
  "pv_area_sqm_est": 45.3,
  "buffer_radius_sqft": 1200,
  "qc_status": "VERIFIABLE",
  "qc_reasons": [],
  "bbox_or_mask": "mask",
  "image_metadata": {
    "source": "esri",
    "zoom": 18,
    "fallback": false
  }
}
\`\`\`

### PNG Overlay (Per Site)

Visual artifact showing:
- Original satellite image
- Detected solar panel bounding boxes/masks
- Confidence scores overlaid

---

## Pipeline Features

| Feature | Description |
|---------|-------------|
| Fetch | Multi-provider satellite imagery (Esri > Google > Bing > OSM) |
| Detect | YOLOv8s binary classification (solar/no-solar) |
| Quantify | Pixel-to-m² area conversion |
| QC | Cloud/shadow/brightness detection |
| Buffer Zones | Primary 1200 sqft, fallback 2400 sqft |
| Explainability | JSON records + PNG overlays (audit-ready) |

---

## Key Parameters

| Parameter | File | Default | Description |
|-----------|------|---------|-------------|
| `conf_thresh` | `detect.py` | 0.25 | Detection confidence threshold |
| `iou_thresh` | `detect.py` | 0.5 | NMS IoU threshold |
| `buffer_sqft_primary` | `inference.py` | 1200 | Primary search radius (sqft) |
| `buffer_sqft_secondary` | `inference.py` | 2400 | Fallback search radius (sqft) |
| `cloud_threshold` | `qc.py` | 220 | Cloud detection brightness |
| `shadow_threshold` | `qc.py` | 40 | Shadow detection darkness |
| `zoom_level` | `utils.py` | 18 (max) | Satellite imagery zoom |

---

## Troubleshooting

### Virtual Environment Issues

\`\`\`powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\activate
\`\`\`

### Module Not Found Error

\`\`\`powershell
.\venv\Scripts\activate
pip install -r environment/requirements.txt
\`\`\`

### Model Not Found Error

Ensure `solar_model.pt` exists in the project root.

### MapTiler API Key Error

Create `.env` file with: `MAPTILER_API_KEY=your_key_here`

### No Detections Found

- Lower `conf_thresh` in `detect.py` (try 0.15)
- Increase `buffer_sqft_secondary` in `inference.py` (try 3600)
- Verify coordinates are correct (latitude, longitude order)

---

## Quick Reference Commands

| Task | Command (PowerShell) |
|------|---------------------|
| Activate venv | `.\venv\Scripts\activate` |
| Install dependencies | `pip install -r environment/requirements.txt` |
| Manual test | `python scripts/test_manual.py` |
| Batch inference | `python run_inference.py` (with `input_sites.xlsx`) |

---

## License

This project is developed for the EcoInnovators 2026 Challenge - PM Surya Ghar scheme verification.
