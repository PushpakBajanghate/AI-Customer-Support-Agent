"""Qdrant-backed retrieval for policies and general support knowledge only."""

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "data" / "policies"
POLICY_TERMS = {
    "policy", "return", "refund", "shipping", "ship", "delivery", "warranty",
    "guarantee", "faq", "exchange", "cancel", "replace", "window", "rules",
    "condition", "packaging", "repair", "service", "technician", "defect", "glitch", "broken", "visit"
}
POLICY_INTENTS = {
    "ORDER_RETURN", "REFUND_REQUEST", "REFUND_STATUS", "ORDER_CANCEL",
    "DELIVERY_DELAY", "DAMAGED_PRODUCT", "WRONG_PRODUCT", "PRODUCT_INFORMATION",
    "GENERAL_QUESTION"
}


def knowledge_retrieval_needed(state: dict[str, Any]) -> bool:
    """Decide whether the message needs semantic policy/FAQ retrieval."""
    message_terms = set(re.findall(r"[a-z]+", state.get("message", "").lower()))
    intent = state.get("intent")
    if intent in POLICY_INTENTS:
        return True
    return bool(message_terms & POLICY_TERMS)


def retrieve_knowledge(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Retrieve policy passages from Qdrant; never query transactional data."""
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from qdrant_client import QdrantClient

        api_key = settings.LLM_API_KEY.strip() if settings.LLM_API_KEY else ""
        if not api_key:
            logger.warning("RAG skipped because embedding API credentials are not configured")
            return []

        embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.RAG_EMBEDDING_MODEL,
            google_api_key=api_key,
        )
        vector = embeddings.embed_query(query)
        client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        if hasattr(client, "search"):
            hits = client.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=vector,
                limit=limit,
                with_payload=True,
            )
        else:
            hits = client.query_points(
                collection_name=settings.QDRANT_COLLECTION,
                query=vector,
                limit=limit,
                with_payload=True,
            ).points
        return [
            {"source": hit.payload.get("source"), "title": hit.payload.get("title"),
             "content": hit.payload.get("content"), "score": hit.score}
            for hit in hits if hit.payload
        ]
    except Exception as exc:
        logger.warning("RAG vector retrieval unavailable: %s; using local policy index", exc)
        return _fallback_local_policy_search(query, limit)


def _fallback_local_policy_search(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Lexical fallback search against markdown files in KNOWLEDGE_DIR."""
    if not KNOWLEDGE_DIR.exists():
        return []
    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored_docs = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        if path.name.startswith("."):
            continue
        try:
            content = path.read_text(encoding="utf-8")
            doc_tokens = set(re.findall(r"[a-z0-9]+", content.lower()))
            overlap = query_tokens & doc_tokens
            if overlap:
                score = len(overlap) / (len(query_tokens) + 1e-5)
                scored_docs.append({
                    "source": path.name,
                    "title": path.stem.replace("_", " ").title(),
                    "content": content.strip(),
                    "score": round(score, 4),
                })
        except Exception:
            continue
    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    return scored_docs[:limit]


def rag_node(state: dict[str, Any]) -> dict[str, Any]:
    if not knowledge_retrieval_needed(state):
        return {**state, "knowledge_context": [], "rag_used": False}
    # Formulate query incorporating message and recent context for multi-turn coherence
    query = state.get("message", "")
    history = state.get("conversation_history", [])
    if history:
        recent_turns = [turn.get("content", "") for turn in history[-2:] if turn.get("content")]
        if recent_turns:
            query = f"{' '.join(recent_turns)} {query}".strip()
    results = retrieve_knowledge(query)
    return {**state, "knowledge_context": results, "rag_used": bool(results)}


def ingest_policy_documents() -> int:
    """Embed and upsert the checked-in policy documents into Qdrant."""
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from qdrant_client import QdrantClient
    from qdrant_client.http import models

    api_key = settings.LLM_API_KEY.strip() if settings.LLM_API_KEY else ""
    if not api_key:
        raise RuntimeError("LLM_API_KEY is required to create policy embeddings")

    documents = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        documents.append({"source": path.name, "title": path.stem, "content": content})
    if not documents:
        raise RuntimeError(f"No policy documents found in {KNOWLEDGE_DIR}")

    embeddings = GoogleGenerativeAIEmbeddings(model=settings.RAG_EMBEDDING_MODEL, google_api_key=api_key)
    vectors = embeddings.embed_documents([document["content"] for document in documents])
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
    collections = {item.name for item in client.get_collections().collections}
    if settings.QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE),
        )
    points = [
        models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, document["source"])),
            vector=vector,
            payload=document,
        )
        for document, vector in zip(documents, vectors)
    ]
    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points, wait=True)
    return len(points)
