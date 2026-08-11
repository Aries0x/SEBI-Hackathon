"""
MarketTrust AI — Seed Script.

Loads reference data into ChromaDB and PostgreSQL for
claim verification and evidence checking.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.config import settings
from app.evidence.loaders import init_chromadb_collections, load_scam_patterns


def main():
    """Run all seed operations."""
    print("=" * 60)
    print("MarketTrust AI — Data Seeder")
    print("=" * 60)

    # Initialize ChromaDB collections
    print("\n1. Initializing ChromaDB collections...")
    init_chromadb_collections()
    print("   ✓ Collections created")

    # Load scam patterns
    print("\n2. Loading scam patterns...")
    count = load_scam_patterns()
    print(f"   ✓ Loaded {count} scam patterns")

    # Load sample SEBI data
    print("\n3. Loading sample SEBI entity data...")
    from app.evidence.loaders import load_sebi_reference_data

    sample_sebi_data = [
        {
            "name": "ICICI Securities Ltd",
            "registration_number": "INZ000183631",
            "type": "Stock Broker",
            "category": "Trading Member",
        },
        {
            "name": "HDFC Securities Ltd",
            "registration_number": "INZ000186937",
            "type": "Stock Broker",
            "category": "Trading Member",
        },
        {
            "name": "Zerodha Broking Ltd",
            "registration_number": "INZ000031633",
            "type": "Stock Broker",
            "category": "Trading Member",
        },
        {
            "name": "Groww (Billionbrains Garage Ventures Pvt Ltd)",
            "registration_number": "INZ000301838",
            "type": "Stock Broker",
            "category": "Trading Member",
        },
        {
            "name": "Motilal Oswal Financial Services Ltd",
            "registration_number": "INZ000158836",
            "type": "Stock Broker",
            "category": "Trading Member",
        },
    ]
    count = load_sebi_reference_data(sample_sebi_data)
    print(f"   ✓ Loaded {count} SEBI entity records")

    print("\n" + "=" * 60)
    print("Seeding complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
