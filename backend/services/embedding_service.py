"""Embedding generation and vector store operations (ChromaDB)."""

from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings

settings = get_settings()
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def get_chroma_client():
    # API and worker processes must share a server, not separate in-memory indexes.
    if settings.CHROMA_HOST:
        return chromadb.HttpClient(
            host=settings.CHROMA_HOST, port=settings.CHROMA_PORT,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection() -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings. Retries transient OpenAI failures with
    exponential backoff (1s, 2s, 4s) before giving up."""
    if not texts:
        return []

    response = openai_client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


def embed_single(text: str) -> list[float]:
    return embed_texts([text])[0]


def store_document_chunks(
    document_id: str, owner_id: str, filename: str, chunks: list[str]
) -> int:
    """Embed and upsert a document's chunks into the vector store.

    owner_id is stored in metadata on every chunk so that search can be
    scoped to a single tenant — this is the enforcement point for
    multi-tenant data isolation at the vector layer.
    """
    collection = get_collection()

    chunk_ids = [f"{document_id}_chunk{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "document_id": document_id,
            "owner_id": owner_id,
            "filename": filename,
            "chunk_index": i,
            "chunk_total": len(chunks),
        }
        for i in range(len(chunks))
    ]

    batch_size = 100
    all_embeddings: list[list[float]] = []
    for i in range(0, len(chunks), batch_size):
        all_embeddings.extend(embed_texts(chunks[i : i + batch_size]))

    collection.upsert(
        ids=chunk_ids,
        embeddings=all_embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return len(chunks)


def search_similar_chunks(
    query: str,
    owner_id: str,
    top_k: int = 5,
    document_ids: list[str] | None = None,
    min_score: float = 0.3,
) -> list[dict]:
    """Return the top_k chunks most similar to query, scoped to owner_id."""
    collection = get_collection()
    if collection.count() == 0 or document_ids == []:
        return []
    query_embedding = embed_single(query)

    if document_ids:
        where_filter = {
            "$and": [
                {"owner_id": {"$eq": owner_id}},
                {"document_id": {"$in": document_ids}},
            ]
        }
    else:
        where_filter = {"owner_id": {"$eq": owner_id}}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        if collection.count() == 0 or "no documents" in str(e).lower():
            return []
        raise

    chunks = []
    if results["ids"] and results["ids"][0]:
        for i, chunk_id in enumerate(results["ids"][0]):
            # ChromaDB returns cosine distance in [0, 2]; convert to a
            # similarity score in [0, 1] where 1 = identical.
            distance = results["distances"][0][i]
            similarity = 1 - (distance / 2)
            if similarity < min_score:
                continue

            metadata = results["metadatas"][0][i]
            chunks.append({
                "chunk_id": chunk_id,
                "text": results["documents"][0][i],
                "document_id": metadata["document_id"],
                "filename": metadata["filename"],
                "chunk_index": metadata["chunk_index"],
                "similarity_score": round(similarity, 4),
            })

    return sorted(chunks, key=lambda x: x["similarity_score"], reverse=True)


def delete_document_chunks(document_id: str, owner_id: str) -> int:
    """Delete vectors only when both document and tenant match."""
    collection = get_collection()
    results = collection.get(
        where={
            "$and": [
                {"document_id": {"$eq": document_id}},
                {"owner_id": {"$eq": owner_id}},
            ]
        },
        include=[],
    )
    if results["ids"]:
        collection.delete(ids=results["ids"])
        return len(results["ids"])
    return 0


def get_collection_stats(owner_id: str) -> dict:
    """Return vector statistics scoped to one tenant."""
    collection = get_collection()
    results = collection.get(where={"owner_id": {"$eq": owner_id}}, include=[])
    return {
        "total_chunks": len(results["ids"] or []),
        "collection_name": settings.CHROMA_COLLECTION_NAME,
    }
