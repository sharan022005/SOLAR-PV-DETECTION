from ultralytics import YOLO
import numpy as np
import warnings
warnings.filterwarnings('ignore')

_model = None

def load_model(model_path="solar_model.pt", device="cpu"):
    """Load YOLO model from path."""
    global _model
    _model = YOLO(model_path, verbose=False)
    _model.to(device)
    return _model

def predict_on_pil(image_pil, conf_thresh=0.25, iou=0.45):
    """
    Run model inference on PIL image.
    Returns: list of detections (dicts with box, conf, cls, mask), raw results
    """
    global _model
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    
    img_np = np.array(image_pil)[:, :, ::-1]  # Convert RGB to BGR
    results = _model.predict(img_np, conf=conf_thresh, iou=iou, verbose=False, imgsz=image_pil.size[0])
    res = results[0]
    dets = []
    boxes = res.boxes
    
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        cls = int(box.cls[0])
        mask = None
        if hasattr(res, 'masks') and res.masks is not None:
            mask = res.masks.data[i].cpu().numpy()
        dets.append({"box": [x1, y1, x2, y2], "conf": conf, "cls": cls, "mask": mask})
    
    return dets, res
