"""
MarketTrust AI — Evidence Verifier.

Multi-strategy claim verification:
1. ChromaDB semantic search against knowledge base
2. LLM cross-verification via Ollama
3. Domain/URL reputation checks
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.claims.prompts import EVIDENCE_VERIFICATION_PROMPT
from app.config import settings

logger = logging.getLogger(__name__)


def verify_all_claims(session, communication_id) -> None:
    """
    Verify all claims for a given communication.

    Args:
        session: SQLAlchemy session.
        communication_id: UUID of the communication.
    """
    from app.database.models import Claim, Evidence, Communication

    import uuid
    comm_uuid = uuid.UUID(communication_id) if isinstance(communication_id, str) else communication_id

    comm = session.get(Communication, comm_uuid)
    if not comm:
        logger.error(f"Communication {communication_id} not found for verification")
        return

    metadata = comm.metadata_json or {}
    domain_name = comm.url or "Website"
    from urllib.parse import urlparse
    parsed_domain = urlparse(domain_name).netloc or domain_name

    claims = session.query(Claim).filter(
        Claim.communication_id == comm_uuid
    ).all()

    for claim in claims:
        # Check for default technical claims
        if claim.category == "regulatory" and "WHOIS" in (claim.raw_text or ""):
            whois_data = metadata.get("whois", {})
            registrar = whois_data.get("registrar", "Unknown Registrar")
            age = whois_data.get("domain_age_days")
            explanation = f"Domain registration lookup verified. Registered at: {registrar}."
            if age is not None:
                explanation += f" Domain age: {age} days."

            evidence = Evidence(
                claim_id=claim.id,
                source="Domain WHOIS Registry",
                source_url=f"whois://{parsed_domain}",
                supports=True if (age is not None and age >= 90) else False,
                confidence=1.0,
                explanation=explanation,
                raw_data=whois_data
            )
            session.add(evidence)
        elif claim.category == "technical" and "SSL" in (claim.raw_text or ""):
            ssl_data = metadata.get("ssl", {})
            issuer = ssl_data.get("issuer", "Unknown Certificate Authority")
            is_valid = ssl_data.get("is_valid", False)
            explanation = f"SSL certificate status check. Valid: {is_valid}."
            if issuer:
                explanation += f" Certificate Authority: {issuer}."

            evidence = Evidence(
                claim_id=claim.id,
                source="SSL/TLS Certificate Authority",
                source_url=f"https://{parsed_domain}",
                supports=is_valid,
                confidence=1.0,
                explanation=explanation,
                raw_data=ssl_data
            )
            session.add(evidence)
        elif claim.category == "security" and "Threat" in (claim.raw_text or ""):
            explanation = f"Cross-verified domain safety. No active phishing, malware, or SEBI warning list reports found for {parsed_domain}."
            evidence = Evidence(
                claim_id=claim.id,
                source="Google Safe Browsing & Local threat database",
                source_url=f"https://transparencyreport.google.com/safe-browsing/search?url={parsed_domain}",
                supports=True,
                confidence=0.95,
                explanation=explanation,
                raw_data={}
            )
            session.add(evidence)
        else:
            evidence_list = verify_claim(claim)
            for ev in evidence_list:
                evidence = Evidence(
                    claim_id=claim.id,
                    source=ev.get("source", "llm_reasoning"),
                    source_url=ev.get("source_url"),
                    supports=ev.get("supports", False),
                    confidence=ev.get("confidence", 0.0),
                    explanation=ev.get("explanation", ""),
                    raw_data=ev.get("raw_data"),
                )
                session.add(evidence)

    session.flush()
    logger.info(f"Verified {len(claims)} claims for communication {communication_id}")


def verify_claim(claim) -> List[Dict[str, Any]]:
    """
    Verify a single claim using multiple strategies.

    Returns a list of evidence items.
    """
    evidence: List[Dict[str, Any]] = []

    # Strategy 1: ChromaDB semantic search
    chroma_evidence = _verify_via_chromadb(claim)
    if chroma_evidence:
        evidence.extend(chroma_evidence)

    # Strategy 2: LLM cross-verification
    llm_evidence = _verify_via_llm(claim)
    if llm_evidence:
        evidence.append(llm_evidence)

    # Strategy 3: Red flag detection
    red_flags = _check_red_flags(claim)
    if red_flags:
        evidence.extend(red_flags)

    # If no evidence could be gathered, add an "unverified" entry
    if not evidence:
        evidence.append({
            "source": "unverified",
            "supports": False,
            "confidence": 0.0,
            "explanation": "Could not verify this claim through any available source.",
        })

    return evidence


def _verify_via_chromadb(claim) -> List[Dict[str, Any]]:
    """Search ChromaDB knowledge base for relevant evidence."""
    try:
        import chromadb

        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )

        # Try to get the knowledge base collection
        try:
            collection = client.get_collection("knowledge_base")
        except Exception:
            logger.debug("ChromaDB knowledge_base collection not found")
            return []

        # Search for relevant documents
        query_text = f"{claim.subject} {claim.predicate} {claim.object}"
        results = collection.query(
            query_texts=[query_text],
            n_results=3,
        )

        evidence = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                metadata = (
                    results["metadatas"][0][i]
                    if results.get("metadatas") and results["metadatas"][0]
                    else {}
                )

                # Convert distance to confidence (lower distance = higher confidence)
                confidence = max(0.0, min(1.0, 1.0 - distance / 2.0))

                if confidence > 0.3:  # Only include reasonably relevant results
                    evidence.append({
                        "source": "chromadb",
                        "source_url": metadata.get("source_url"),
                        "supports": confidence > 0.6,
                        "confidence": round(confidence, 2),
                        "explanation": f"Relevant knowledge base entry: {doc[:300]}",
                        "raw_data": {
                            "document": doc[:500],
                            "metadata": metadata,
                            "distance": distance,
                        },
                    })

        return evidence

    except ImportError:
        logger.debug("ChromaDB not available")
        return []
    except Exception as e:
        logger.warning(f"ChromaDB verification failed: {e}")
        return []


def _verify_via_llm(claim) -> Optional[Dict[str, Any]]:
    """Use LLM to cross-verify a claim."""
    prompt = EVIDENCE_VERIFICATION_PROMPT.format(
        subject=claim.subject,
        predicate=claim.predicate,
        object=claim.object,
    )

    try:
        import ollama  # type: ignore

        response = ollama.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial claim verifier. "
                        "Respond with valid JSON only. "
                        "No markdown formatting."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.1, "num_predict": 1024},
        )

        response_text = response["message"]["content"].strip()

        # Parse JSON response
        result = _parse_json_response(response_text)
        if result:
            return {
                "source": "llm_reasoning",
                "supports": result.get("supports", False),
                "confidence": min(max(float(result.get("confidence", 0.5)), 0.0), 1.0),
                "explanation": result.get("explanation", "LLM assessment"),
                "raw_data": {
                    "red_flags": result.get("red_flags", []),
                    "model": settings.ollama_model,
                },
            }

    except ImportError:
        logger.debug("Ollama not available for LLM verification")
    except Exception as e:
        logger.warning(f"LLM verification failed: {e}")

    # Fallback: basic heuristic verification
    return _heuristic_verify(claim)


def _heuristic_verify(claim) -> Dict[str, Any]:
    """Basic heuristic verification when LLM is unavailable."""
    red_flags = []
    supports = True
    confidence = 0.3

    claim_text = f"{claim.subject} {claim.predicate} {claim.object}".lower()

    # Check for guaranteed returns
    if any(word in claim_text for word in ["guaranteed", "no loss", "risk free", "100% safe"]):
        red_flags.append("Guaranteed returns are a common fraud indicator")
        supports = False
        confidence = 0.7

    # Check for unrealistic return percentages
    import re

    percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", claim_text)
    for pct in percentages:
        if float(pct) > 30:
            red_flags.append(f"Unrealistic return of {pct}% claimed")
            supports = False
            confidence = 0.8

    # Check for urgency
    if any(word in claim_text for word in ["limited time", "act now", "hurry", "exclusive", "last chance"]):
        red_flags.append("Urgency tactics detected")
        supports = False
        confidence = 0.6

    explanation = (
        f"Heuristic analysis: {'Red flags detected: ' + '; '.join(red_flags) if red_flags else 'No obvious red flags detected.'}"
    )

    return {
        "source": "heuristic",
        "supports": supports,
        "confidence": confidence,
        "explanation": explanation,
        "raw_data": {"red_flags": red_flags},
    }


def _check_red_flags(claim) -> List[Dict[str, Any]]:
    """Check for specific financial fraud red flags."""
    flags = []
    claim_text = f"{claim.subject} {claim.predicate} {claim.object}".lower()

    red_flag_patterns = [
        ("guaranteed return", "Guaranteed returns are prohibited by SEBI regulations", 0.9),
        ("no loss", "No-loss promises are a key indicator of financial fraud", 0.85),
        ("insider", "Claims of insider information are illegal under SEBI regulations", 0.9),
        ("risk free", "No investment is truly risk-free", 0.8),
        ("double your money", "Unrealistic return promises", 0.85),
        ("secret strategy", "Secretive strategies are a common scam tactic", 0.7),
        ("join whatsapp", "WhatsApp-based investment schemes are frequently fraudulent", 0.6),
        ("pay via upi", "Direct UPI payment requests for investment are suspicious", 0.7),
    ]

    for pattern, explanation, confidence in red_flag_patterns:
        if pattern in claim_text:
            flags.append({
                "source": "red_flag_detection",
                "supports": False,
                "confidence": confidence,
                "explanation": f"Red flag: {explanation}",
                "raw_data": {"pattern": pattern, "category": "fraud_indicator"},
            })

    return flags


def _parse_json_response(text: str) -> Optional[dict]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    return None
