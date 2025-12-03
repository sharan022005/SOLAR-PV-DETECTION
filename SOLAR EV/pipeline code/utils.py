import math
import os
import io
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import requests

def sqft_to_radius_meters(sqft):
    """Convert area in sqft to equivalent circle radius in meters."""
    radius_feet = math.sqrt(sqft / math.pi)
    radius_m = radius_feet * 0.3048
    return radius_m

def latlon_to_zoom_for_width(lat_deg, target_ground_width_m, image_width_px=640):
    """Compute zoom level so that image_width_px covers target_ground_width_m at given latitude."""
    meters_per_pixel = target_ground_width_m / image_width_px
    zoom = math.log2((156543.03392 * math.cos(math.radians(lat_deg))) / meters_per_pixel)
    zoom = max(0, min(18, int(round(zoom))))
    return zoom

def is_no_data_tile(img):
    """
    Detect if a tile is a 'Map data not yet available' placeholder.
    These tiles are typically uniform gray with white text.
    """
    if img is None:
        return True
    
    # Convert to numpy array
    arr = np.array(img)
    
    # Check if the image is mostly a single gray color (placeholder)
    # Esri placeholder tiles are typically RGB(200, 200, 200) or similar gray
    if arr.ndim == 3:
        # Calculate color variance - real satellite images have high variance
        variance = np.var(arr)
        
        # Check if mostly gray (low variance and gray-ish mean)
        mean_color = np.mean(arr, axis=(0, 1))
        is_gray = np.std(mean_color) < 10  # R, G, B are very similar
        is_uniform = variance < 500  # Very low pixel variance
        
        # Also check for specific gray placeholder color
        gray_threshold = np.all(np.abs(mean_color - 200) < 30)
        
        if (is_gray and is_uniform) or gray_threshold:
            return True
    
    return False

def download_maptiler_static_sat(lat, lon, radius_m, api_key, size=640, scale=2, maptype="satellite"):
    """
    Download satellite image using multiple providers with fallback.
    Priority: Esri World Imagery -> Google Static Maps -> Bing Maps -> OSM Standard
    """
    ground_width_m = radius_m * 2
    initial_zoom = latlon_to_zoom_for_width(lat, ground_width_m, image_width_px=size)
    
    for zoom in range(initial_zoom, 14, -1):  # Try down to zoom 15
        try:
            print(f"[INFO] Trying Esri World Imagery at zoom {zoom}...")
            img = download_osm_esri_tiles(lat, lon, zoom, size)
            
            # Check if we got valid imagery (not placeholder)
            if not is_no_data_tile(img):
                metadata = {"source": "esri_world_imagery", "zoom": zoom}
                print(f"[INFO] Successfully got satellite imagery at zoom {zoom}")
                return img, metadata
            else:
                print(f"[WARNING] Esri returned placeholder at zoom {zoom}, trying lower zoom...")
        except Exception as e:
            print(f"[WARNING] Esri failed at zoom {zoom}: {e}")
    
    google_api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if google_api_key and google_api_key != "YOUR_GOOGLE_MAPS_API_KEY":
        try:
            print(f"[INFO] Trying Google Static Maps API...")
            img, metadata = download_google_static_maps(lat, lon, initial_zoom, size, google_api_key)
            if img and not is_no_data_tile(img):
                return img, metadata
        except Exception as e:
            print(f"[WARNING] Google Static Maps failed: {e}")
    
    # Fallback to Bing Maps aerial
    try:
        print(f"[INFO] Trying Bing Maps aerial...")
        img = download_bing_aerial(lat, lon, initial_zoom, size)
        if img and not is_no_data_tile(img):
            metadata = {"source": "bing_aerial", "zoom": initial_zoom}
            return img, metadata
    except Exception as e:
        print(f"[WARNING] Bing Maps failed: {e}")
    
    # Last resort - OSM standard map
    print(f"[WARNING] All satellite sources failed, using OSM standard map")
    img = download_osm_standard_map(lat, lon, min(initial_zoom, 18), size)
    metadata = {"source": "osm_standard_fallback", "zoom": initial_zoom}
    return img, metadata

def download_google_static_maps(lat, lon, zoom, size, api_key):
    """
    Download satellite image from Google Static Maps API.
    Requires a valid API key with Static Maps API enabled.
    """
    url = f"https://maps.googleapis.com/maps/api/staticmap"
    params = {
        "center": f"{lat},{lon}",
        "zoom": min(zoom, 20),  # Google supports up to zoom 21
        "size": f"{size}x{size}",
        "maptype": "satellite",
        "key": api_key
    }
    
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    
    img = Image.open(io.BytesIO(resp.content)).convert('RGB')
    metadata = {"source": "google_static_maps", "zoom": zoom}
    
    return img, metadata

def download_bing_aerial(lat, lon, zoom, size=640):
    """
    Download aerial imagery from Bing Maps using quadkey tiles.
    """
    def latlon_to_tile(lat, lon, zoom):
        n = 2 ** zoom
        x = int(((lon + 180) / 360) * n)
        y = int(((1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat))) / math.pi) / 2) * n)
        return x, y
    
    def tile_to_quadkey(x, y, zoom):
        quadkey = ""
        for i in range(zoom, 0, -1):
            digit = 0
            mask = 1 << (i - 1)
            if (x & mask) != 0:
                digit += 1
            if (y & mask) != 0:
                digit += 2
            quadkey += str(digit)
        return quadkey
    
    def latlon_to_tile_fraction(lat, lon, zoom):
        n = 2 ** zoom
        x = ((lon + 180) / 360) * n
        y = ((1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat))) / math.pi) / 2) * n
        return x, y
    
    zoom = min(zoom, 19)
    center_x, center_y = latlon_to_tile(lat, lon, zoom)
    frac_x, frac_y = latlon_to_tile_fraction(lat, lon, zoom)
    
    offset_x = int((frac_x - center_x) * 256)
    offset_y = int((frac_y - center_y) * 256)
    
    tile_size = 256
    canvas = Image.new('RGB', (768, 768), color=(200, 200, 200))
    
    tiles_downloaded = 0
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tile_x = center_x + dx
            tile_y = center_y + dy
            
            max_tile = 2 ** zoom - 1
            if tile_x < 0 or tile_x > max_tile or tile_y < 0 or tile_y > max_tile:
                continue
            
            quadkey = tile_to_quadkey(tile_x, tile_y, zoom)
            # Bing Maps aerial tile URL
            url = f"https://ecn.t0.tiles.virtualearth.net/tiles/a{quadkey}.jpeg?g=1"
            
            try:
                resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0 Solar-PV-Detection/1.0'})
                resp.raise_for_status()
                tile_img = Image.open(io.BytesIO(resp.content)).convert('RGB')
                tile_img = tile_img.resize((tile_size, tile_size))
                paste_x = (dx + 1) * tile_size
                paste_y = (dy + 1) * tile_size
                canvas.paste(tile_img, (paste_x, paste_y))
                tiles_downloaded += 1
            except Exception as e:
                print(f"[WARNING] Failed to download Bing tile: {e}")
    
    if tiles_downloaded == 0:
        raise Exception("Failed to download any Bing tiles")
    
    center_px = 384 + offset_x
    center_py = 384 + offset_y
    
    left = max(0, min(center_px - size // 2, 768 - size))
    top = max(0, min(center_py - size // 2, 768 - size))
    
    img = canvas.crop((left, top, left + size, top + size))
    return img

def download_osm_esri_tiles(lat, lon, zoom, size=640):
    """
    Download satellite imagery from Esri World Imagery (free, no API key).
    Tiles 256x256, we'll stitch multiple to cover the requested area.
    """
    # Convert lat/lon to tile coordinates
    def latlon_to_tile(lat, lon, zoom):
        n = 2 ** zoom
        x = ((lon + 180) / 360) * n
        y = ((1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat))) / math.pi) / 2) * n
        return int(x), int(y)
    
    def latlon_to_tile_fraction(lat, lon, zoom):
        n = 2 ** zoom
        x = ((lon + 180) / 360) * n
        y = ((1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat))) / math.pi) / 2) * n
        return x, y
    
    center_x, center_y = latlon_to_tile(lat, lon, zoom)
    frac_x, frac_y = latlon_to_tile_fraction(lat, lon, zoom)
    
    offset_x = int((frac_x - center_x) * 256)
    offset_y = int((frac_y - center_y) * 256)
    
    # Download 3x3 tiles centered on location for better coverage
    tile_size = 256
    canvas = Image.new('RGB', (768, 768), color=(200, 200, 200))  # Gray fallback
    
    tiles_downloaded = 0
    valid_tiles = 0  # Track tiles that aren't placeholders
    
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tile_x = center_x + dx
            tile_y = center_y + dy
            
            max_tile = 2 ** zoom - 1
            if tile_x < 0 or tile_x > max_tile or tile_y < 0 or tile_y > max_tile:
                print(f"[WARNING] Tile {zoom}/{tile_y}/{tile_x} out of bounds, skipping")
                continue
            
            # Esri World Imagery URL
            url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{tile_y}/{tile_x}"
            
            try:
                resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0 Solar-PV-Detection/1.0'})
                resp.raise_for_status()
                tile_img = Image.open(io.BytesIO(resp.content)).convert('RGB')
                tile_img = tile_img.resize((tile_size, tile_size))
                paste_x = (dx + 1) * tile_size
                paste_y = (dy + 1) * tile_size
                canvas.paste(tile_img, (paste_x, paste_y))
                tiles_downloaded += 1
                
                if not is_no_data_tile(tile_img):
                    valid_tiles += 1
                    
            except Exception as e:
                print(f"[WARNING] Failed to download tile {zoom}/{tile_y}/{tile_x}: {e}")
    
    if tiles_downloaded == 0:
        raise Exception("Failed to download any tiles")
    
    if valid_tiles < 5:  # Need at least 5 of 9 valid tiles
        print(f"[WARNING] Only {valid_tiles}/9 tiles have valid imagery")
    
    center_px = 384 + offset_x  # 384 = center of 768px canvas
    center_py = 384 + offset_y
    
    left = center_px - size // 2
    top = center_py - size // 2
    right = left + size
    bottom = top + size
    
    # Ensure crop stays within canvas bounds
    left = max(0, min(left, 768 - size))
    top = max(0, min(top, 768 - size))
    right = left + size
    bottom = top + size
    
    img = canvas.crop((left, top, right, bottom))
    
    print(f"[INFO] Created {size}x{size} image from {tiles_downloaded} tiles ({valid_tiles} valid) at zoom {zoom}")
    return img

def download_osm_standard_map(lat, lon, zoom, size=640):
    """
    Fallback: OpenStreetMap standard map tiles (free).
    Less detailed than satellite but always available.
    """
    def latlon_to_tile(lat, lon, zoom):
        n = 2 ** zoom
        x = ((lon + 180) / 360) * n
        y = ((1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat))) / math.pi) / 2) * n
        return int(x), int(y)
    
    def latlon_to_tile_fraction(lat, lon, zoom):
        n = 2 ** zoom
        x = ((lon + 180) / 360) * n
        y = ((1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat))) / math.pi) / 2) * n
        return x, y
    
    center_x, center_y = latlon_to_tile(lat, lon, zoom)
    frac_x, frac_y = latlon_to_tile_fraction(lat, lon, zoom)
    
    offset_x = int((frac_x - center_x) * 256)
    offset_y = int((frac_y - center_y) * 256)
    
    tile_size = 256
    canvas = Image.new('RGB', (768, 768), color=(200, 200, 200))
    
    tiles_downloaded = 0
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tile_x = center_x + dx
            tile_y = center_y + dy
            
            max_tile = 2 ** zoom - 1
            if tile_x < 0 or tile_x > max_tile or tile_y < 0 or tile_y > max_tile:
                print(f"[WARNING] OSM Tile {zoom}/{tile_x}/{tile_y} out of bounds, skipping")
                continue
            
            # OpenStreetMap tile server (note: OSM uses /z/x/y format)
            url = f"https://tile.openstreetmap.org/{zoom}/{tile_x}/{tile_y}.png"
            
            try:
                resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0 Solar-PV-Detection/1.0'})
                resp.raise_for_status()
                tile_img = Image.open(io.BytesIO(resp.content)).convert('RGB')
                tile_img = tile_img.resize((tile_size, tile_size))
                paste_x = (dx + 1) * tile_size
                paste_y = (dy + 1) * tile_size
                canvas.paste(tile_img, (paste_x, paste_y))
                tiles_downloaded += 1
            except Exception as e:
                print(f"[WARNING] Failed to download OSM tile {zoom}/{tile_x}/{tile_y}: {e}")
    
    if tiles_downloaded == 0:
        raise Exception("Failed to download OSM tiles")
    
    center_px = 384 + offset_x
    center_py = 384 + offset_y
    
    left = max(0, min(center_px - size // 2, 768 - size))
    top = max(0, min(center_py - size // 2, 768 - size))
    
    img = canvas.crop((left, top, left + size, top + size))
    
    return img

# Keep the old function name as alias for backward compatibility
def download_google_static_sat(lat, lon, radius_m, api_key, size=640, scale=2, maptype="satellite"):
    """Deprecated: Use download_maptiler_static_sat instead. Kept for backward compatibility."""
    return download_maptiler_static_sat(lat, lon, radius_m, api_key, size, scale, maptype)

def save_overlay(image_pil, masks=None, boxes=None, buffer_radius_px=None, out_path="overlay.png"):
    """
    Save overlay with masks, boxes, and buffer circle.
    image_pil: PIL.Image
    masks: list of binary numpy arrays
    boxes: list of (x1,y1,x2,y2)
    buffer_radius_px: int (draw circle at center)
    """
    im = image_pil.copy()
    draw = ImageDraw.Draw(im, "RGBA")
    w, h = im.size
    cx, cy = w//2, h//2
    
    # Draw buffer circle
    if buffer_radius_px:
        draw.ellipse([cx-buffer_radius_px, cy-buffer_radius_px, cx+buffer_radius_px, cy+buffer_radius_px],
                     outline=(255,255,0,180), width=3)
    
    # Draw masks
    if masks:
        for mask in masks:
            if mask is None:
                continue
            mask_img = Image.fromarray((mask.astype('uint8')*150).astype('uint8')).convert('L').resize(im.size)
            colored = Image.new("RGBA", im.size, (0,255,0,80))
            im.paste(colored, (0,0), mask_img)
    
    # Draw boxes
    if boxes:
        for box in boxes:
            draw.rectangle(box, outline=(255,0,0,255), width=3)
    
    im.save(out_path)
    return out_path
