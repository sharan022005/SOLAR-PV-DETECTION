"""
Manual testing script - test a single coordinate before batch processing.
Run this to verify your pipeline works on one sample.
"""
import os
import sys
import json
from pathlib import Path
from .inference import process_row
from .detect import load_model

def test_single_coordinate(sample_id=999, latitude=40.7128, longitude=-74.0060, 
                          model_path="solar_model.pt",
                          output_folder="test_output"):
    """
    Test pipeline on a single coordinate.
    
    Args:
        sample_id: Test identifier
        latitude: Test lat (WGS84)
        longitude: Test lon (WGS84)
        model_path: Path to trained .pt file
        output_folder: Where to save test results
    
    Returns:
        result dict (same format as batch inference)
    
    Example:
        test_single_coordinate(sample_id=1, latitude=40.7128, longitude=-74.0060)
    """
    
    print("=" * 70)
    print("SOLAR PV DETECTION - SINGLE COORDINATE TEST")
    print("=" * 70)
    print(f"Sample ID: {sample_id}")
    print(f"Latitude: {latitude}")
    print(f"Longitude: {longitude}")
    print(f"Model: {model_path}")
    print(f"Output Folder: {output_folder}")
    print("-" * 70)
    
    # Verify model exists
    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}")
        print("Please ensure solar_model.pt exists in current directory")
        return None
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    try:
        # Load model
        print("\n1. Loading model...")
        model = load_model(model_path)
        print("   Model loaded successfully!")
        
        # Process single row
        print("\n2. Fetching satellite image...")
        print("   (This will call MapTiler Static Maps API)")
        
        result = process_row(
            sample_id=sample_id,
            lat=latitude,
            lon=longitude,
            model=model,
            out_folder=output_folder,
            buffer_sqft_primary=1200,
            buffer_sqft_secondary=2400
        )
        
        # Print results
        print("\n3. INFERENCE RESULTS:")
        print("-" * 70)
        print(f"   Sample ID:        {result['sample_id']}")
        print(f"   Has Solar:        {result['has_solar']}")
        print(f"   Confidence:       {result['confidence']:.4f}")
        print(f"   Area (m²):        {result['pv_area_sqm_est']}")
        print(f"   Buffer (sqft):    {result['buffer_radius_sqft']}")
        print(f"   QC Status:        {result['qc_status']}")
        if result.get('qc_reasons'):
            print(f"   QC Reasons:       {', '.join(result['qc_reasons'])}")
        print(f"   Detection Type:   {result.get('bbox_or_mask', 'N/A')}")
        print("-" * 70)
        
        # Print output locations
        print("\n4. OUTPUT LOCATIONS:")
        json_path = os.path.join(output_folder, f"{sample_id}.json")
        overlay_path = os.path.join(output_folder, f"{sample_id}_overlay.png")
        
        if os.path.exists(json_path):
            print(f"   JSON:    {json_path}")
        if os.path.exists(overlay_path):
            print(f"   Overlay: {overlay_path}")
        
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        
        return result
        
    except Exception as e:
        print(f"\nERROR during inference: {e}")
        import traceback
        traceback.print_exc()
        return None
