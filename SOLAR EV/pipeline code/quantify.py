import numpy as np
from PIL import Image

def pixels_to_m2(num_pixels, meters_per_pixel):
    """Convert pixel count to square meters."""
    return num_pixels * (meters_per_pixel ** 2)

def compute_selected_panel_area(detections, image_size_px, radius_m, selected_index=0):
    """
    Compute solar panel area using best detection with buffer zone.
    Returns: area_m2, mask_pixels, selected_mask (binary numpy)
    """
    w, h = image_size_px
    meters_per_pixel = (2 * radius_m) / w
    
    best_idx = None
    best_overlap = 0
    mask_pixels = 0
    selected_mask = None
    
    cx, cy = w // 2, h // 2
    
    for idx, d in enumerate(detections):
        mask = d.get("mask", None)
        
        if mask is None:
            # Use bounding box as fallback
            x1, y1, x2, y2 = map(int, d["box"])
            m = np.zeros((h, w), dtype=bool)
            x1c, x2c = max(0, x1), min(w-1, x2)
            y1c, y2c = max(0, y1), min(h-1, y2)
            m[y1c:y2c, x1c:x2c] = True
        else:
            m = mask.astype(bool)
            if m.shape != (h, w):
                mm = Image.fromarray(m.astype('uint8')*255).resize((w, h), resample=Image.NEAREST)
                m = (np.array(mm) > 0)
        
        # Compute buffer circle
        yy, xx = np.ogrid[:h, :w]
        radius_px = int((radius_m * 1.0) / meters_per_pixel)
        circle = (xx - cx)**2 + (yy - cy)**2 <= (radius_px**2)
        overlap = np.logical_and(m, circle).sum()
        
        if overlap > best_overlap:
            best_overlap = overlap
            best_idx = idx
            mask_pixels = m.sum()
            selected_mask = m
    
    if best_idx is None:
        return 0.0, 0, None
    
    area_m2 = pixels_to_m2(mask_pixels, meters_per_pixel)
    return area_m2, mask_pixels, selected_mask
