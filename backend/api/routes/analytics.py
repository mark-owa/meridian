"""Aggregate usage analytics for the dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.deps import get_current_user
from models.database import Document, Extraction, Lead, QueryLog, User, get_db
from models.schemas import DashboardStats

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardStats)
def dashboard_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owner_id = current_user.id

    total_documents = db.query(func.count(Document.id)).filter(
        Document.owner_id == owner_id
    ).scalar() or 0

    documents_ready = db.query(func.count(Document.id)).filter(
        Document.owner_id == owner_id, Document.status == "ready"
    ).scalar() or 0

    total_queries = db.query(func.count(QueryLog.id)).filter(
        QueryLog.user_id == owner_id
    ).scalar() or 0

    avg_response_time = db.query(func.avg(QueryLog.response_time_ms)).filter(
        QueryLog.user_id == owner_id
    ).scalar()

    total_leads = db.query(func.count(Lead.id)).filter(Lead.owner_id == owner_id).scalar() or 0

    qualified_leads = db.query(func.count(Lead.id)).filter(
        Lead.owner_id == owner_id, Lead.status.in_(["qualified", "contacted", "converted"])
    ).scalar() or 0

    avg_lead_score = db.query(func.avg(Lead.qualification_score)).filter(
        Lead.owner_id == owner_id, Lead.qualification_score.isnot(None)
    ).scalar()

    total_extractions = db.query(func.count(Extraction.id)).join(
        Document, Document.id == Extraction.document_id
    ).filter(Document.owner_id == owner_id).scalar() or 0

    return DashboardStats(
        total_documents=total_documents,
        documents_ready=documents_ready,
        total_queries=total_queries,
        avg_response_time_ms=round(float(avg_response_time), 1) if avg_response_time is not None else None,
        total_leads=total_leads,
        qualified_leads=qualified_leads,
        avg_lead_score=round(float(avg_lead_score), 1) if avg_lead_score is not None else None,
        total_extractions=total_extractions,
    )
