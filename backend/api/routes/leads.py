"""Lead management and AI qualification endpoints."""


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from models.database import User, get_db
from models.schemas import LeadCreate, LeadListResponse, LeadResponse, MessageResponse
from services.lead_service import (
    batch_qualify_leads,
    create_lead,
    delete_lead,
    get_leads,
    qualify_lead,
    update_lead_status,
)

router = APIRouter(prefix="/leads", tags=["Lead Qualification"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def add_lead(
    lead_data: LeadCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return create_lead(lead_data, current_user.id, db)


@router.get("", response_model=LeadListResponse)
def list_leads(
    status_filter: str | None = Query(None, alias="status"),
    min_score: int | None = Query(None, ge=0, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_leads(current_user.id, db, status_filter, min_score, skip, limit)


@router.post("/{lead_id}/qualify", response_model=LeadResponse)
def run_qualification(
    lead_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Score the lead and draft an outreach email (two model calls)."""
    return qualify_lead(lead_id, current_user.id, db)


@router.post("/qualify-batch", response_model=list[LeadResponse])
def run_batch_qualification(
    limit: int = Query(10, ge=1, le=25),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Qualify up to `limit` new leads synchronously (two model calls each)."""
    return batch_qualify_leads(current_user.id, db, limit)


@router.patch("/{lead_id}/status", response_model=LeadResponse)
def change_lead_status(
    lead_id: str,
    new_status: str = Query(..., alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_lead_status(lead_id, new_status, current_user.id, db)


@router.delete("/{lead_id}", response_model=MessageResponse)
def remove_lead(lead_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_lead(lead_id, current_user.id, db)
    return MessageResponse(message="Lead deleted successfully")
