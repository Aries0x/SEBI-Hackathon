"""
MarketTrust AI — Image Analyzer.

Extracts metadata, runs OCR, and performs forgery detection
(Error Level Analysis) on uploaded images.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)


def extract_metadata(image_path: str) -> Dict[str, Any]:
    """
    Extract EXIF metadata from an image file.

    Returns dict with camera info, GPS coordinates, timestamps, etc.
    """
    metadata: Dict[str, Any] = {}

    try:
        img = Image.open(image_path)
        metadata["format"] = img.format
        metadata["size"] = {"width": img.width, "height": img.height}
        metadata["mode"] = img.mode

        # Extract EXIF data
        exif_data = img._getexif()
        if exif_data:
            exif: Dict[str, Any] = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                # Skip binary blobs
                if isinstance(value, bytes) and len(value) > 100:
                    exif[tag_name] = f"<binary data {len(value)} bytes>"
                else:
                    try:
                        exif[tag_name] = str(value)
                    except Exception:
                        exif[tag_name] = "<unparseable>"
            metadata["exif"] = exif

            # Extract GPS if available
            gps_info = exif_data.get(34853)
            if gps_info:
                gps = _parse_gps(gps_info)
                if gps:
                    metadata["gps"] = gps

    except Exception as e:
        logger.error(f"Failed to extract image metadata: {e}")
        metadata["error"] = str(e)

    return metadata


def _parse_gps(gps_info: dict) -> Optional[Dict[str, float]]:
    """Parse GPS coordinates from EXIF GPSInfo tag."""
    try:
        gps_data = {}
        for key, val in gps_info.items():
            tag = GPSTAGS.get(key, key)
            gps_data[tag] = val

        lat = gps_data.get("GPSLatitude")
        lat_ref = gps_data.get("GPSLatitudeRef")
        lon = gps_data.get("GPSLongitude")
        lon_ref = gps_data.get("GPSLongitudeRef")

        if lat and lon:
            lat_deg = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / 3600
            lon_deg = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / 3600

            if lat_ref == "S":
                lat_deg = -lat_deg
            if lon_ref == "W":
                lon_deg = -lon_deg

            return {"latitude": lat_deg, "longitude": lon_deg}
    except Exception as e:
        logger.warning(f"GPS parsing failed: {e}")

    return None


def run_ocr(image_path: str) -> str:
    """
    Extract text from image using PaddleOCR.

    Args:
        image_path: Path to the image file.

    Returns:
        Extracted text as a single string.
    """
    try:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        result = ocr.ocr(image_path, cls=True)

        text_parts: List[str] = []
        if result and result[0]:
            for line in result[0]:
                if line and len(line) > 1 and line[1]:
                    text = line[1][0] if isinstance(line[1], tuple) else str(line[1])
                    text_parts.append(text)

        full_text = " ".join(text_parts)
        logger.info(f"OCR extracted {len(text_parts)} text regions from {image_path}")
        return full_text

    except ImportError:
        logger.warning("PaddleOCR not installed, skipping OCR")
        return ""
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


def check_forgery(image_path: str) -> Dict[str, Any]:
    """
    Perform Error Level Analysis (ELA) for potential image manipulation detection.

    Compares the image against a re-compressed version to find regions
    with inconsistent compression levels (potential edits).

    Returns dict with forgery analysis results.
    """
    try:
        # Read original image
        original = cv2.imread(image_path)
        if original is None:
            return {"error": "Cannot read image", "is_suspicious": False}

        # Re-save at known quality
        import tempfile

        tmp_path = tempfile.mktemp(suffix=".jpg")
        cv2.imwrite(tmp_path, original, [cv2.IMWRITE_JPEG_QUALITY, 90])

        # Read re-compressed
        recompressed = cv2.imread(tmp_path)

        # Compute difference
        diff = cv2.absdiff(original, recompressed)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

        # Scale for visibility
        scale = 20
        diff_scaled = cv2.multiply(diff_gray, scale)

        # Statistics
        mean_diff = float(np.mean(diff_gray))
        max_diff = float(np.max(diff_gray))
        std_diff = float(np.std(diff_gray))

        # Determine if suspicious
        # High variance in ELA suggests potential manipulation
        is_suspicious = std_diff > 15.0 or max_diff > 100

        # Find suspicious regions (high ELA values)
        threshold = max(mean_diff + 2 * std_diff, 30)
        suspicious_mask = diff_gray > threshold
        suspicious_percentage = float(np.sum(suspicious_mask)) / suspicious_mask.size * 100

        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)

        result = {
            "is_suspicious": is_suspicious,
            "mean_ela_difference": round(mean_diff, 2),
            "max_ela_difference": round(max_diff, 2),
            "std_ela_difference": round(std_diff, 2),
            "suspicious_area_percentage": round(suspicious_percentage, 2),
            "analysis": (
                "Potential manipulation detected — inconsistent compression levels found."
                if is_suspicious
                else "No obvious signs of manipulation detected."
            ),
        }

        logger.info(
            f"ELA analysis for {image_path}: "
            f"suspicious={is_suspicious}, mean_diff={mean_diff:.2f}"
        )
        return result

    except Exception as e:
        logger.error(f"Forgery check failed: {e}")
        return {"error": str(e), "is_suspicious": False}
