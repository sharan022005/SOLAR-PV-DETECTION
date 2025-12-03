import os
import json
import pandas as pd
from PIL import Image
from pathlib import Path
from .fetch_image import fetch_for_coordinate
from .detect import load_model, predict_on_pil
from .quantify import compute_selected_panel_area
from .qc import qc_decision
from .utils import save_overlay

def process_row(sample_id, lat, lon, model, out_folder, buffer_sqft_primary=1200, buffer_sqft_secondary=2400):
    """
    Process single location: fetch image, detect, quantify, QC.
    Returns record dict with results.
    """
    img, metadata, radius_m = fetch_for_coordinate(lat, lon, buffer_sqft_primary, size=640)
    detections, raw = predict_on_pil(img)
    qc_status, reasons = qc_decision(img, detections)
    
    chosen_buffer = buffer_sqft_primary
    area_m2 = 0.0
    confidence = 0.0
    bbox_or_mask = None
    overlay_path = None
    
    if detections:
        area_m2, mask_pixels, mask = compute_selected_panel_area(detections, img.size, radius_m)
        confidence = max([d["conf"] for d in detections]) if detections else 0.0
        bbox_or_mask = "mask" if mask is not None else "bbox"
    else:
        # Try secondary buffer
        img2, metadata2, radius_m2 = fetch_for_coordinate(lat, lon, buffer_sqft_secondary, size=640)
        detections2, raw2 = predict_on_pil(img2)
        if detections2:
            img = img2
            metadata = metadata2
            radius_m = radius_m2
            chosen_buffer = buffer_sqft_secondary
            area_m2, mask_pixels, mask = compute_selected_panel_area(detections2, img.size, radius_m)
            confidence = max([d["conf"] for d in detections2])
            bbox_or_mask = "mask" if mask is not None else "bbox"
            qc_status, reasons = qc_decision(img, detections2)
    
    # Save overlay
    all_masks = [d.get("mask") for d in (detections if detections else [])]
    all_boxes = [d["box"] for d in (detections if detections else [])]
    out_overlay = os.path.join(out_folder, f"{sample_id}_overlay.png")
    
    try:
        save_overlay(img, masks=all_masks, boxes=all_boxes, out_path=out_overlay)
        overlay_path = out_overlay
    except Exception as e:
        overlay_path = None
    
    record = {
        "sample_id": int(sample_id),
        "lat": float(lat),
        "lon": float(lon),
        "has_solar": bool(area_m2 > 0.1),
        "confidence": float(confidence),
        "pv_area_sqm_est": float(round(area_m2, 3)),
        "buffer_radius_sqft": int(chosen_buffer),
        "qc_status": qc_status,
        "qc_reasons": reasons,
        "bbox_or_mask": bbox_or_mask,
        "image_metadata": metadata
    }
    
    # Save JSON
    with open(os.path.join(out_folder, f"{sample_id}.json"), "w") as f:
        json.dump(record, f, indent=2)
    
    return record

def run_inference_on_excel(excel_path, model_path, output_folder):
    """
    Run end-to-end inference on all rows in Excel/CSV file.
    Excel should have: sample_id, latitude (or lat), longitude (or lon)
    """
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Loading model from: {model_path}")
    model = load_model(model_path)
    
    print(f"Reading file: {excel_path}")
    
    try:
        file_ext = Path(excel_path).suffix.lower()
        
        # Try different read methods based on file extension
        if file_ext == '.csv':
            df = pd.read_csv(excel_path)
        elif file_ext in ['.xlsx', '.xls']:
            try:
                # Try openpyxl first for modern .xlsx
                df = pd.read_excel(excel_path, engine='openpyxl')
            except Exception as e:
                print(f"  openpyxl failed: {e}")
                print("  Trying xlrd engine...")
                try:
                    df = pd.read_excel(excel_path, engine='xlrd')
                except:
                    print("  Both engines failed. File might be corrupted or CSV with wrong extension.")
                    print("  Attempting to read as CSV...")
                    df = pd.read_csv(excel_path)
        else:
            # Try CSV as fallback
            print(f"  Unknown extension '{file_ext}', attempting CSV read...")
            df = pd.read_csv(excel_path)
        
        print(f"✓ Successfully loaded {len(df)} rows")
        
    except Exception as e:
        print(f"✗ ERROR: Could not read file {excel_path}")
        print(f"  Details: {e}")
        print("\n  Troubleshooting:")
        print("  1. Ensure file exists and has .csv or .xlsx extension")
        print("  2. If Excel file is corrupted, save as CSV and try again")
        print("  3. Required columns: sample_id, latitude (or lat), longitude (or lon)")
        return None
    
    required_cols = ['sample_id']
    lat_col = 'latitude' if 'latitude' in df.columns else 'lat' if 'lat' in df.columns else None
    lon_col = 'longitude' if 'longitude' in df.columns else 'lon' if 'lon' in df.columns else None
    
    if not lat_col or not lon_col:
        print(f"✗ ERROR: Missing latitude/longitude columns")
        print(f"  Available columns: {list(df.columns)}")
        print(f"  Expected: 'sample_id', and either 'latitude'/'longitude' or 'lat'/'lon'")
        return None
    
    results = []
    for idx, row in df.iterrows():
        sample_id = row["sample_id"]
        lat = row[lat_col]
        lon = row[lon_col]
        print(f"[{idx+1}/{len(df)}] Processing: {sample_id} ({lat:.4f}, {lon:.4f})")
        
        try:
            rec = process_row(sample_id, lat, lon, model, output_folder)
            results.append(rec)
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "sample_id": int(sample_id),
                "lat": float(lat),
                "lon": float(lon),
                "error": str(e)
            })
    
    # Save aggregated results
    with open(os.path.join(output_folder, "predictions.json"), "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nAll done! Outputs in: {output_folder}")
    return results
