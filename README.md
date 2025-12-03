-----

# Solar PV Detection Pipeline

  

**An AI-powered pipeline for detecting and quantifying rooftop solar panels using YOLOv8 and satellite imagery.**

This project is developed for the **EcoInnovators 2026 Challenge** to verify installations for the PM Surya Ghar scheme. It automates the process of fetching satellite imagery, detecting solar panels, and calculating their estimated surface area.

-----

## Project Structure

```text
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
└── README.md                   # Project documentation
```

-----

## Development Environment

  * **IDE:** Visual Studio Code (Windows)
  * **Dataset Management:** Google Drive + Google Colab
  * **Model Training:** Google Colab (T4 GPU)
  * **Inference:** Local Windows Machine (CPU/GPU)

-----

## Setup Instructions

### 1\. Prerequisites

  * Python 3.10+ installed.
  * Visual Studio Code installed.

### 2\. Create Virtual Environment

Open your VS Code terminal (` Ctrl +  ` \`) and run:

```powershell
# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\activate
```

*Note: If you encounter an execution policy error, run:*

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\activate
```

### 3\. Install Dependencies

```powershell
pip install -r environment/requirements.txt
```

### 4\. Configure API Keys

You need a MapTiler API key for satellite imagery. Get one for free [here](https://cloud.maptiler.com/account/keys/).

**Option A (Recommended):** Create a `.env` file in the root directory:

```env
MAPTILER_API_KEY=your_actual_api_key_here
```

**Option B (Temporary):** Set it in your terminal session:

```powershell
$env:MAPTILER_API_KEY="your_actual_api_key_here"
```

-----

## Model Training (Methodology)

The model was trained using free GPU resources on Google Colab.

### Dataset Preparation

We combined three distinct Roboflow datasets:

1.  Alfred Weber Institute Dataset
2.  LSGI547 Project Dataset
3.  Piscinas Y Tenistable Dataset

**Workflow:**

1.  Datasets uploaded to Google Drive.
2.  Merged via Colab into a unified structure (`train`/`val`).

### Training Configuration

| Parameter | Value |
| :--- | :--- |
| **Base Model** | YOLOv8s (`yolov8s.pt`) |
| **Epochs** | 30 |
| **Image Size** | 640x640 |
| **Batch Size** | 16 |
| **Device** | T4 GPU (Colab) |

**Outputs:**

  * `solar_model.pt`: Final weights (placed in project root).
  * `runs/detect/train/results.csv`: Metrics.

-----

## Running Inference

### Option 1: Quick Manual Test

Test a single coordinate defined in the script.

```powershell
.\venv\Scripts\activate
python scripts/test_manual.py
```

**Output:** Check `test_output/` for `1.json` and `1_overlay.png`.

### Option 2: Batch Processing (Excel)

Process multiple sites defined in an Excel file.

1.  Create `input_sites.xlsx`:
    | sample\_id | latitude | longitude |
    | :--- | :--- | :--- |
    | 1 | 40.7128 | -74.0060 |
    | 2 | 34.0522 | -118.2437 |

2.  Run the inference script:

    ```powershell
    python run_inference.py
    ```

**Output:** Check `predictions/` for JSON reports and visual overlays.

-----

## Output Format

### JSON Report (Per Site)

```json
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
    "zoom": 18
  }
}
```

### Visual Overlay

A PNG image is generated for every site, showing:

  * Original satellite tile.
  * Predicted bounding boxes/masks.
  * Confidence scores.

-----

## Key Parameters

| Parameter | File | Default | Description |
| :--- | :--- | :--- | :--- |
| `conf_thresh` | `detect.py` | 0.25 | Minimum confidence to accept a detection. |
| `iou_thresh` | `detect.py` | 0.5 | NMS threshold to remove duplicates. |
| `buffer_sqft_primary` | `inference.py` | 1200 | Primary search radius around coordinate. |
| `cloud_threshold` | `qc.py` | 220 | Brightness level to detect clouds. |

-----

## Troubleshooting

  * **`Module Not Found`**: Ensure you activated the venv and ran `pip install -r environment/requirements.txt`.
  * **`Model Not Found`**: Ensure `solar_model.pt` is in the root directory.
  * **`MapTiler Error`**: Check your `.env` file or environment variable.
  * **No Detections?**:
      * Try lowering `conf_thresh` to 0.15 in `detect.py`.
      * Verify your latitude/longitude order (Lat, Lon).

-----

## License

## 📜 License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)** - see the [LICENSE](LICENSE) file for details.

**Note:** This project utilizes [YOLOv8](https://github.com/ultralytics/ultralytics) by Ultralytics, which is licensed under AGPL-3.0. As a derivative work, this pipeline is also distributed under AGPL-3.0 to comply with open-source requirements.

