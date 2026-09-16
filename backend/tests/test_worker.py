"""Document retries must preserve a useful final state."""

from unittest.mock import Mock

from models.database import Document
from worker.tasks import process_document


def test_exhausted_worker_failure_records_status_even_if_cleanup_fails(
    db_session, registered_user, monkeypatch,
):
    doc = Document(owner_id=registered_user["id"], filename="failed.txt",
                   original_name="failed.txt", file_type="txt", file_size_bytes=10,
                   status="processing")
    db_session.add(doc)
    db_session.commit()
    monkeypatch.setattr("worker.tasks.delete_document_chunks",
                        Mock(side_effect=RuntimeError("vector store unavailable")))
    monkeypatch.setattr("worker.tasks.extract_text_from_file",
                        Mock(side_effect=ValueError("parse failed")))
    # apply() exercises Celery's retry exhaustion and on_failure hook.
    result = process_document.apply(args=[doc.id], retries=2, throw=False)
    assert result.failed()
    db_session.refresh(doc)
    assert doc.status == "failed"
    assert doc.chunk_count == 0
    assert doc.processed_at is not None
    assert "Check the worker logs" in doc.error_message
