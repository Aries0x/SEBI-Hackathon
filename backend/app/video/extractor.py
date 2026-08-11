"""
MarketTrust AI — Video Extractor.

Extracts metadata, keyframes, and audio from video files using
FFprobe, OpenCV, and FFmpeg.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def extract_metadata(video_path: str) -> Dict[str, Any]:
    """
    Extract video metadata using FFprobe.

    Returns dict with duration, resolution, codec, fps, etc.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        metadata = json.loads(result.stdout)

        # Extract key fields
        fmt = metadata.get("format", {})
        video_stream = next(
            (s for s in metadata.get("streams", []) if s.get("codec_type") == "video"),
            {},
        )
        audio_stream = next(
            (s for s in metadata.get("streams", []) if s.get("codec_type") == "audio"),
            {},
        )

        return {
            "duration": float(fmt.get("duration", 0)),
            "size_bytes": int(fmt.get("size", 0)),
            "format_name": fmt.get("format_name", "unknown"),
            "bit_rate": int(fmt.get("bit_rate", 0)),
            "video_codec": video_stream.get("codec_name", "unknown"),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream.get("r_frame_rate") else 0,
            "audio_codec": audio_stream.get("codec_name", "none"),
            "audio_sample_rate": int(audio_stream.get("sample_rate", 0)),
            "raw": metadata,
        }
    except Exception as e:
        logger.error(f"Failed to extract video metadata: {e}")
        return {"error": str(e)}


def extract_frames(
    video_path: str,
    output_dir: str,
    max_frames: int = 20,
    method: str = "scene_change",
) -> List[str]:
    """
    Extract keyframes from video using scene change detection.

    Args:
        video_path: Path to the video file.
        output_dir: Directory to save extracted frames.
        max_frames: Maximum number of frames to extract.
        method: 'scene_change' or 'uniform'.

    Returns:
        List of paths to extracted frame images.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_paths: List[str] = []

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if method == "scene_change":
        frame_paths = _extract_scene_change_frames(
            cap, total_frames, output_path, max_frames
        )
    else:
        # Uniform sampling
        interval = max(1, total_frames // max_frames)
        for i in range(0, total_frames, interval):
            if len(frame_paths) >= max_frames:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                path = str(output_path / f"frame_{i:06d}.jpg")
                cv2.imwrite(path, frame)
                frame_paths.append(path)

    cap.release()
    logger.info(f"Extracted {len(frame_paths)} frames from {video_path}")
    return frame_paths


def _extract_scene_change_frames(
    cap: cv2.VideoCapture,
    total_frames: int,
    output_path: Path,
    max_frames: int,
    threshold: float = 30.0,
) -> List[str]:
    """Extract frames at scene changes using histogram difference."""
    frame_paths: List[str] = []
    prev_hist = None

    # Sample at most every Nth frame for efficiency
    sample_interval = max(1, total_frames // (max_frames * 10))

    for i in range(0, total_frames, sample_interval):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            break

        # Compute histogram
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()

        # Compare with previous
        if prev_hist is not None:
            diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CHISQR)
            if diff > threshold:
                path = str(output_path / f"frame_{i:06d}.jpg")
                cv2.imwrite(path, frame)
                frame_paths.append(path)
                if len(frame_paths) >= max_frames:
                    break
        else:
            # Always capture first frame
            path = str(output_path / f"frame_{i:06d}.jpg")
            cv2.imwrite(path, frame)
            frame_paths.append(path)

        prev_hist = hist

    return frame_paths


def extract_audio(video_path: str, output_path: str) -> str:
    """
    Extract audio track from video using FFmpeg.

    Args:
        video_path: Path to the video file.
        output_path: Path for the output audio file (WAV).

    Returns:
        Path to the extracted audio file.
    """
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i", video_path,
                "-vn",                    # No video
                "-acodec", "pcm_s16le",  # PCM 16-bit WAV
                "-ar", "16000",          # 16kHz sample rate (for Whisper)
                "-ac", "1",              # Mono
                "-y",                    # Overwrite
                output_path,
            ],
            capture_output=True,
            timeout=120,
            check=True,
        )
        logger.info(f"Extracted audio to {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg audio extraction failed: {e.stderr.decode()}")
        raise
