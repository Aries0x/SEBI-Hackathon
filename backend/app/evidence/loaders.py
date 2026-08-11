"""
MarketTrust AI — Evidence Knowledge Base Loaders.

Scripts to pre-load reference data into ChromaDB for
claim verification (SEBI broker lists, scam patterns, etc.).
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


def init_chromadb_collections() -> None:
    """Initialize ChromaDB collections for the knowledge base."""
    try:
        import chromadb

        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )

        # Create or get the knowledge base collection
        client.get_or_create_collection(
            name="knowledge_base",
            metadata={"description": "General financial knowledge base"},
        )

        # Create or get the SEBI entities collection
        client.get_or_create_collection(
            name="sebi_entities",
            metadata={"description": "SEBI registered entities"},
        )

        logger.info("ChromaDB collections initialized")

    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")


def load_sebi_reference_data(data: List[Dict[str, str]]) -> int:
    """
    Load SEBI registered entity data into ChromaDB.

    Args:
        data: List of dicts with 'name', 'registration_number', 'type', etc.

    Returns:
        Number of records loaded.
    """
    try:
        import chromadb

        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        collection = client.get_or_create_collection("sebi_entities")

        documents = []
        metadatas = []
        ids = []

        for i, entity in enumerate(data):
            doc = (
                f"{entity.get('name', '')} is a SEBI registered "
                f"{entity.get('type', 'entity')} with registration number "
                f"{entity.get('registration_number', 'N/A')}. "
                f"Category: {entity.get('category', 'N/A')}."
            )
            documents.append(doc)
            metadatas.append({
                "name": entity.get("name", ""),
                "registration_number": entity.get("registration_number", ""),
                "type": entity.get("type", ""),
                "source": "sebi_database",
                "source_url": "https://www.sebi.gov.in/",
            })
            ids.append(f"sebi_{i}")

        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

        logger.info(f"Loaded {len(documents)} SEBI entity records into ChromaDB")
        return len(documents)

    except Exception as e:
        logger.error(f"Failed to load SEBI reference data: {e}")
        return 0


def load_scam_patterns() -> int:
    """
    Load known financial scam patterns into the knowledge base.

    Returns:
        Number of patterns loaded.
    """
    patterns = [
        {
            "text": "Guaranteed returns above 15% per annum are not possible in legitimate regulated investments. Any scheme promising guaranteed high returns is likely fraudulent.",
            "category": "guaranteed_returns",
        },
        {
            "text": "SEBI has never authorized any entity to give assured returns. Any claim of SEBI authorization for guaranteed returns is false.",
            "category": "sebi_misrepresentation",
        },
        {
            "text": "Legitimate stock brokers are registered with SEBI and operate through recognized stock exchanges (NSE/BSE). Unregistered entities offering stock tips are illegal.",
            "category": "unregistered_broker",
        },
        {
            "text": "Investment advice through WhatsApp groups, Telegram channels, or social media without proper SEBI registration is illegal under SEBI regulations.",
            "category": "unauthorized_advice",
        },
        {
            "text": "Ponzi schemes promise high returns with little risk, using money from new investors to pay earlier investors. They inevitably collapse.",
            "category": "ponzi_scheme",
        },
        {
            "text": "Tip services that charge upfront fees and promise specific stock returns are often fraudulent. SEBI registered investment advisors must follow strict guidelines.",
            "category": "tip_fraud",
        },
        {
            "text": "Claims of insider trading information are illegal. Trading on insider information violates SEBI (Prohibition of Insider Trading) Regulations.",
            "category": "insider_trading",
        },
        {
            "text": "Pump-and-dump schemes involve artificially inflating stock prices through false claims, then selling when the price rises. Common in penny stocks.",
            "category": "pump_and_dump",
        },
        {
            "text": "Fixed deposit schemes by unregistered companies offering rates significantly above RBI/bank rates are likely fraudulent.",
            "category": "fake_fixed_deposit",
        },
        {
            "text": "Any investment scheme that requires recruiting others to earn returns (multi-level marketing structure) is likely a pyramid scheme.",
            "category": "pyramid_scheme",
        },
    ]

    try:
        import chromadb

        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        collection = client.get_or_create_collection("knowledge_base")

        documents = [p["text"] for p in patterns]
        metadatas = [
            {
                "category": p["category"],
                "source": "sebi_guidelines",
                "source_url": "https://www.sebi.gov.in/",
            }
            for p in patterns
        ]
        ids = [f"scam_pattern_{i}" for i in range(len(patterns))]

        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info(f"Loaded {len(patterns)} scam patterns into ChromaDB")
        return len(patterns)

    except Exception as e:
        logger.error(f"Failed to load scam patterns: {e}")
        return 0
