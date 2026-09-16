"""Retrieval-augmented generation pipeline for the knowledge base."""

import time

from fastapi import HTTPException
from openai import OpenAI
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings
from models.database import QueryLog
from models.schemas import KnowledgeQueryResponse, SourceChunk
from services.embedding_service import search_similar_chunks
from utils.prompts import rag_answer_prompt

settings = get_settings()
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=8))
def _generate_answer(prompt: dict):
    return openai_client.chat.completions.create(
        model=settings.CHAT_MODEL,
        messages=[
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ],
        temperature=0.1,  # Factual retrieval favors consistency over creativity
        max_tokens=1500,
    )


def query_knowledge_base(
    query: str,
    owner_id: str,
    user_id: str,
    db: Session,
    top_k: int | None = None,
    document_ids: list[str] | None = None,
) -> KnowledgeQueryResponse:
    """Retrieve relevant chunks, synthesize a cited answer, and log the query."""
    start_time = time.time()
    k = top_k or settings.TOP_K_RESULTS

    similar_chunks = search_similar_chunks(
        query=query,
        owner_id=owner_id,
        top_k=k,
        document_ids=document_ids,
        min_score=settings.MIN_SIMILARITY_SCORE,
    )

    if similar_chunks:
        context_texts = [chunk["text"] for chunk in similar_chunks]
        response = _generate_answer(rag_answer_prompt(query, context_texts))
        answer_text = response.choices[0].message.content
        if not answer_text or not answer_text.strip():
            raise HTTPException(status_code=502, detail="The answer model returned no text")
        tokens_used = response.usage.total_tokens if response.usage else 0
    else:
        answer_text = (
            "I couldn't find anything relevant in the knowledge base. "
            "Try uploading a related document or rephrasing the question."
        )
        tokens_used = 0
    response_time_ms = int((time.time() - start_time) * 1000)

    sources = [
        SourceChunk(
            document_id=chunk["document_id"],
            document_name=chunk["filename"],
            chunk_text=chunk["text"][:300] + "..." if len(chunk["text"]) > 300 else chunk["text"],
            similarity_score=chunk["similarity_score"],
            chunk_index=chunk["chunk_index"],
        )
        for chunk in similar_chunks
    ]

    db.add(QueryLog(
        user_id=user_id,
        query_text=query,
        answer_text=answer_text,
        sources_used=[
            {"document_id": c["document_id"], "filename": c["filename"]} for c in similar_chunks
        ],
        tokens_used=tokens_used,
        response_time_ms=response_time_ms,
    ))
    db.commit()

    return KnowledgeQueryResponse(
        query=query,
        answer=answer_text,
        sources=sources,
        tokens_used=tokens_used,
        response_time_ms=response_time_ms,
    )


def get_query_history(user_id: str, db: Session, limit: int = 20) -> list[QueryLog]:
    return (
        db.query(QueryLog)
        .filter(QueryLog.user_id == user_id)
        .order_by(QueryLog.created_at.desc())
        .limit(limit)
        .all()
    )
