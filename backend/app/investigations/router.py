"""
MarketTrust AI — Investigation Input Adapter.

Routes incoming investigations to the correct media pipeline
based on the detected media type.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def dispatch_to_pipeline(communication_id: str, media_type: str) -> Optional[str]:
    """
    Dispatch a communication to the appropriate processing pipeline.

    Args:
        communication_id: UUID of the communication to process.
        media_type: One of 'video', 'image', 'email', 'website'.

    Returns:
        The Celery task ID, or None if dispatch failed.
    """
    try:
        if media_type == "video":
            from app.video.tasks import process_video

            result = process_video.delay(communication_id)
        elif media_type == "image":
            from app.image.tasks import process_image

            result = process_image.delay(communication_id)
        elif media_type == "email":
            from app.email.tasks import process_email

            result = process_email.delay(communication_id)
        elif media_type == "website":
            from app.website.tasks import process_website

            result = process_website.delay(communication_id)
        else:
            logger.error(f"Unknown media type: {media_type}")
            return None

        logger.info(
            f"Dispatched {media_type} pipeline for communication {communication_id}, "
            f"task_id={result.id}"
        )
        return result.id

    except Exception as e:
        logger.error(
            f"Failed to dispatch {media_type} pipeline "
            f"for communication {communication_id}: {e}"
        )
        return None
