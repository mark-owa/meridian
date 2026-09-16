"""Document upload and management endpoints.

Text extraction, chunking, and embedding happen asynchronously via a Celery
task (see worker/tasks.py) — upload returns immediately with status
'pending', and clients poll GET /documents/{id} until status is 'ready'.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from models.database import User, get_db
from models.schemas import DocumentListResponse, DocumentResponse, MessageResponse
from services.document_service import delete_document, get_document, list_documents, save_upload
from services.embedding_service import delete_document_chunks
from worker.tasks import process_document

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(..., description="PDF, TXT, or DOCX file"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a document for knowledge-base indexing. Processing runs in the
    background; poll GET /documents/{id} for status."""
    doc = await save_upload(file, current_user.id, db)
    try:
        process_document.delay(doc.id)
    except Exception as exc:
        # Do not leave an orphaned pending document/file if the broker is unavailable.
        from services.document_service import UPLOAD_DIR
        file_path = UPLOAD_DIR / doc.filename
        file_path.unlink(missing_ok=True)
        db.delete(doc)
        db.commit()
        raise HTTPException(status_code=503, detail="Document processing is unavailable; retry later") from exc
    return doc


@router.get("", response_model=DocumentListResponse)
def list_user_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs, total = list_documents(db, current_user.id, skip, limit)
    return DocumentListResponse(documents=docs, total=total)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_single_document(
    document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return get_document(db, document_id, current_user.id)


@router.delete("/{document_id}", response_model=MessageResponse)
def remove_document(
    document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete a document, its file on disk, and its vector embeddings."""
    doc = get_document(db, document_id, current_user.id)
    original_name = doc.original_name

    deleted_chunks = delete_document_chunks(document_id, current_user.id)
    delete_document(db, document_id, current_user.id)

    return MessageResponse(
        message=f"Document '{original_name}' deleted successfully",
        detail=f"Removed {deleted_chunks} vector chunks from the knowledge base",
    )
