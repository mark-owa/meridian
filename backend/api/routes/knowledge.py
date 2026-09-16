"""Knowledge base query endpoints (retrieval-augmented generation)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_current_user
from models.database import User, get_db
from models.schemas import KnowledgeQueryRequest, KnowledgeQueryResponse
from services.embedding_service import get_collection_stats
from services.rag_service import get_query_history, query_knowledge_base

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.post("/query", response_model=KnowledgeQueryResponse)
def ask_question(
    request: KnowledgeQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a natural-language question against the user's document set.
    Answers are grounded only in retrieved chunks, with sources cited."""
    return query_knowledge_base(
        query=request.query,
        owner_id=current_user.id,
        user_id=current_user.id,
        db=db,
        top_k=request.top_k,
        document_ids=request.document_ids,
    )


@router.get("/history")
def query_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    history = get_query_history(current_user.id, db, limit)
    return [
        {
            "id": h.id,
            "query": h.query_text,
            "answer": h.answer_text,
            "created_at": h.created_at,
            "response_time_ms": h.response_time_ms,
        }
        for h in history
    ]


@router.get("/stats")
def knowledge_base_stats(current_user: User = Depends(get_current_user)):
    return get_collection_stats(current_user.id)
