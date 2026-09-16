"""Background jobs that run on the Celery worker process, not the API process."""

import logging

from celery import Task

from config import get_settings
from models.database import Document, SessionLocal
from services.document_service import UPLOAD_DIR, extract_text_from_file, update_document_status
from services.embedding_service import delete_document_chunks, store_document_chunks
from utils.chunking import smart_chunk
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


class DocumentTask(Task):
    """Record exhausted processing failures and attempt vector cleanup."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        document_id = args[0] if args else kwargs.get("document_id")
        if document_id:
            db = SessionLocal()
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    try:
                        delete_document_chunks(document_id, document.owner_id)
                    except Exception:
                        logger.exception("Vector cleanup failed for %s", document_id)
                    update_document_status(
                        db, document_id, status="failed",
                        error_message="Document processing failed. Check the worker logs.",
                    )
            finally:
                db.close()
        logger.error("Document processing failed for %s: %s", document_id, exc)


@celery_app.task(
    base=DocumentTask,
    bind=True,
    max_retries=2,
    default_retry_delay=15,
)
def process_document(self, document_id: str) -> dict:
    """Extract text, chunk it, embed the chunks, and mark the document ready.

    This is the one place document_id -> Document row lookups happen for
    the ingestion pipeline; the route layer never re-implements it.
    """
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.warning("process_document called for missing document %s", document_id)
            return {"status": "skipped", "reason": "document not found"}
        if document.status == "ready":
            return {"status": "ready", "chunk_count": document.chunk_count}

        update_document_status(db, document_id, status="processing")

        file_path = UPLOAD_DIR / document.filename
        text = extract_text_from_file(file_path, document.file_type)

        if not text or not text.strip():
            update_document_status(
                db, document_id, status="failed", error_message="No extractable text found"
            )
            return {"status": "failed", "reason": "empty document"}

        settings = get_settings()
        chunks = smart_chunk(
            text, chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP,
            document_type="general",
        )
        chunk_count = store_document_chunks(
            document_id=document.id,
            owner_id=document.owner_id,
            filename=document.original_name,
            chunks=chunks,
        )

        updated = update_document_status(db, document_id, status="ready", chunk_count=chunk_count)
        if updated is None:
            # Deletion may finish while this worker is waiting for embeddings.
            delete_document_chunks(document_id, document.owner_id)
            return {"status": "skipped", "reason": "document deleted during processing"}
        return {"status": "ready", "chunk_count": chunk_count}

    except Exception as exc:
        db.rollback()
        # Celery re-raises exc when retries are exhausted; on_failure handles it.
        raise self.retry(exc=exc) from exc
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1)
def batch_qualify_leads_task(self, owner_id: str, limit: int = 25) -> dict:
    """Qualify a larger batch of leads than the synchronous endpoint allows,
    without holding an HTTP request open while it runs."""
    from services.lead_service import batch_qualify_leads

    db = SessionLocal()
    try:
        results = batch_qualify_leads(owner_id, db, limit=limit)
        return {"status": "completed", "qualified_count": len(results)}
    finally:
        db.close()
