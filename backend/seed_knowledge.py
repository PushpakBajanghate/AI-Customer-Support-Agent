"""Load policy markdown files into the configured Qdrant collection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.rag.knowledge import ingest_policy_documents


if __name__ == "__main__":
    print(f"Indexed {ingest_policy_documents()} knowledge documents into Qdrant")
