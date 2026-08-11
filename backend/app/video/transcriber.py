"""
MarketTrust AI — Video Transcriber.

Speech-to-text transcription using Faster Whisper for
extracting spoken content from video audio tracks.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def transcribe(
    audio_path: str,
    model_size: str = "base",
    language: Optional[str] = None,
) -> Dict:
    """
    Transcribe audio to text using Faster Whisper.

    Args:
        audio_path: Path to the audio file (WAV, 16kHz mono).
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large-v3').
        language: Language code (e.g., 'en', 'hi'). Auto-detect if None.

    Returns:
        Dict with 'text' (full transcript), 'segments' (timestamped), and 'language'.
    """
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(model_size, device="auto", compute_type="auto")

        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # Filter out silence
        )

        transcript_segments: List[Dict] = []
        full_text_parts: List[str] = []

        for segment in segments:
            seg_data = {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
            }
            transcript_segments.append(seg_data)
            full_text_parts.append(segment.text.strip())

        full_text = " ".join(full_text_parts)

        logger.info(
            f"Transcribed {audio_path}: {len(transcript_segments)} segments, "
            f"language={info.language}, prob={info.language_probability:.2f}"
        )

        return {
            "text": full_text,
            "segments": transcript_segments,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
        }

    except ImportError:
        logger.warning("faster-whisper not installed, returning empty transcript")
        return {
            "text": "",
            "segments": [],
            "language": "unknown",
            "language_probability": 0.0,
            "duration": 0.0,
        }
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {
            "text": "",
            "segments": [],
            "language": "unknown",
            "language_probability": 0.0,
            "duration": 0.0,
            "error": str(e),
        }
