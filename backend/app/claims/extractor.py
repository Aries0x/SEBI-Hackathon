"""
MarketTrust AI — Claim Extractor.

Uses Qwen3 via Ollama to extract structured factual claims
from text extracted by the media pipelines.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from app.claims.prompts import CLAIM_EXTRACTION_PROMPT
from app.config import settings

logger = logging.getLogger(__name__)


def extract_claims(text: str) -> List[Dict[str, Any]]:
    """
    Extract verifiable claims from text using LLM.

    Args:
        text: The extracted text from a communication (transcript, OCR, email body, etc.)

    Returns:
        List of claim dicts with subject, predicate, object, confidence, raw_text, category.
    """
    if not text or not text.strip():
        logger.info("No text provided for claim extraction")
        return []

    # Truncate very long texts to fit context window
    max_chars = 8000
    truncated_text = text[:max_chars]
    if len(text) > max_chars:
        truncated_text += "\n... [text truncated]"

    prompt = CLAIM_EXTRACTION_PROMPT.format(text=truncated_text)

    try:
        response_text = _call_ollama(prompt)
        claims = _parse_claims_response(response_text)

        logger.info(f"Extracted {len(claims)} claims from text ({len(text)} chars)")
        return claims

    except Exception as e:
        logger.error(f"Claim extraction failed: {e}")
        return []


def _call_ollama(prompt: str) -> str:
    """
    Call the Ollama API with the given prompt.

    Returns the raw text response.
    """
    try:
        import ollama  # type: ignore

        response = ollama.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial claim extraction AI. "
                        "Always respond with valid JSON only. "
                        "No markdown formatting, no explanations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": 0.1,  # Low temperature for deterministic output
                "num_predict": 4096,
            },
        )

        return response["message"]["content"]

    except ImportError:
        logger.warning("Ollama library not installed, using fallback extraction")
        return _fallback_extract(prompt)
    except Exception as e:
        logger.error(f"Ollama API call failed: {e}")
        return _fallback_extract(prompt)


def _fallback_extract(prompt: str) -> str:
    """
    Fallback claim extraction using simple heuristics
    when Ollama/LLM is not available.
    """
    # Extract text from the prompt
    text = prompt.split("Text to analyze:\n")[-1] if "Text to analyze:" in prompt else prompt

    claims = []

    # Simple pattern matching for common financial claims
    import re

    # Look for percentage patterns
    pct_patterns = re.findall(
        r"(\d+(?:\.\d+)?)\s*%\s*(return|profit|growth|gain|loss|interest)",
        text,
        re.IGNORECASE,
    )
    for pct, claim_type in pct_patterns:
        claims.append({
            "subject": "Communication",
            "predicate": f"claims {claim_type}",
            "object": f"{pct}% {claim_type}",
            "confidence": 0.6,
            "raw_text": f"{pct}% {claim_type}",
            "category": "financial",
        })

    # Look for SEBI registration claims
    sebi_patterns = re.findall(
        r"SEBI\s+(?:registered|approved|licensed|reg\.?\s*no\.?)\s*:?\s*([\w/-]+)?",
        text,
        re.IGNORECASE,
    )
    for reg_no in sebi_patterns:
        claims.append({
            "subject": "Entity",
            "predicate": "claims SEBI registration",
            "object": f"Registration: {reg_no}" if reg_no else "SEBI registered",
            "confidence": 0.7,
            "raw_text": f"SEBI registered {reg_no}",
            "category": "regulatory",
        })

    # Look for guarantee claims
    guarantee_patterns = re.findall(
        r"(guaranteed?\s+return|no[\s-]*loss|risk[\s-]*free|100%\s*safe)",
        text,
        re.IGNORECASE,
    )
    for pattern in guarantee_patterns:
        claims.append({
            "subject": "Communication",
            "predicate": "promises",
            "object": pattern.strip(),
            "confidence": 0.8,
            "raw_text": pattern.strip(),
            "category": "prediction",
        })

    return json.dumps(claims)


def _parse_claims_response(response_text: str) -> List[Dict[str, Any]]:
    """Parse the LLM response into a list of claim dicts."""
    # Try to find JSON array in the response
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # Try parsing directly
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return _validate_claims(result)
    except json.JSONDecodeError:
        pass

    # Try to find JSON array within the text
    import re

    json_match = re.search(r"\[.*\]", text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group())
            if isinstance(result, list):
                return _validate_claims(result)
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not parse claims from LLM response: {text[:200]}")
    return []


def _validate_claims(claims: list) -> List[Dict[str, Any]]:
    """Validate and normalize claim dicts."""
    valid_claims = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue

        valid_claim = {
            "subject": str(claim.get("subject", ""))[:500],
            "predicate": str(claim.get("predicate", ""))[:500],
            "object": str(claim.get("object", ""))[:500],
            "confidence": min(max(float(claim.get("confidence", 0.5)), 0.0), 1.0),
            "raw_text": str(claim.get("raw_text", ""))[:1000],
            "category": str(claim.get("category", ""))[:100] or None,
        }

        # Skip claims with empty required fields
        if valid_claim["subject"] and valid_claim["predicate"] and valid_claim["object"]:
            valid_claims.append(valid_claim)

    return valid_claims
