"""Document data extraction endpoints (invoices, contracts, receipts)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from models.database import User, get_db
from models.schemas import ExtractionRequest, ExtractionResponse
from services.extraction_service import (
    extract_document_data,
    get_extraction,
    list_extractions_for_document,
)

router = APIRouter(prefix="/extraction", tags=["Document Intelligence"])


@router.post("/run", response_model=ExtractionResponse)
def run_extraction(
    request: ExtractionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Extract structured data from a document that has finished indexing
    (status must be 'ready'). Synchronous — typically returns in a few
    seconds, so this doesn't need the background task queue."""
    return extract_document_data(request, current_user.id, db)


@router.get("/{extraction_id}", response_model=ExtractionResponse)
def get_extraction_result(
    extraction_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return get_extraction(extraction_id, current_user.id, db)


@router.get("/document/{document_id}", response_model=list[ExtractionResponse])
def list_document_extractions(
    document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return list_extractions_for_document(document_id, current_user.id, db)
