from PIL import ImageStat, Image
import numpy as np

def resolution_check(image_pil, min_pixels=300):
    """Check if image has minimum resolution."""
    w, h = image_pil.size
    return (w >= min_pixels and h >= min_pixels)

def brightness_check(image_pil, min_brightness=20):
    """Check if image has minimum brightness (not too dark)."""
    stat = ImageStat.Stat(image_pil.convert('L'))
    return stat.mean[0] >= min_brightness

def cloud_shadow_check(image_pil, shadow_threshold=40, cloud_threshold=220):
    """Check for excessive cloud/shadow coverage."""
    im = np.array(image_pil.convert('L'))
    bright_frac = (im > cloud_threshold).sum() / im.size
    dark_frac = (im < shadow_threshold).sum() / im.size
    if bright_frac > 0.4 or dark_frac > 0.4:
        return False
    return True

def qc_decision(image_pil, detections):
    """
    Returns: qc_status ('VERIFIABLE' or 'NOT_VERIFIABLE'), reasons list
    """
    reasons = []
    if not resolution_check(image_pil):
        reasons.append("low_resolution")
    if not brightness_check(image_pil):
        reasons.append("low_brightness")
    if not cloud_shadow_check(image_pil):
        reasons.append("cloud_or_shadow")
    if not detections:
        reasons.append("no_detection")
    
    if reasons:
        return "NOT_VERIFIABLE", reasons
    return "VERIFIABLE", []
