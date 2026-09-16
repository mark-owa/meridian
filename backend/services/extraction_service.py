"""AI-driven structured data extraction from uploaded documents.

Pipeline: document text -> LLM prompt -> JSON -> Pydantic validation -> DB row.
The Pydantic validation step matters: it rejects malformed model output
before it ever reaches downstream systems or storage.
"""

import json
import math
import re
from collections.abc import Callable

from fastapi import HTTPException, status
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings
from models.database import Document, Extraction
from models.schemas import (
    ContractData,
    DocumentType,
    ExtractionRequest,
    ExtractionResponse,
    InvoiceData,
    ReceiptData,
)
from services.document_service import UPLOAD_DIR, extract_text_from_file, get_document
from utils.prompts import (
    contract_extraction_prompt,
    invoice_extraction_prompt,
    receipt_extraction_prompt,
)

settings = get_settings()
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

EXTRACTION_CONFIG: dict[DocumentType, tuple[Callable, type[BaseModel]]] = {
    DocumentType.invoice: (invoice_extraction_prompt, InvoiceData),
    DocumentType.contract: (contract_extraction_prompt, ContractData),
    DocumentType.receipt: (receipt_extraction_prompt, ReceiptData),
}


def _clean_json_response(raw: str) -> str:
    """Strip ```json ... ``` fences the model sometimes wraps output in."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    return re.sub(r"\s*```$", "", cleaned).strip()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=8))
def _call_extraction_model(prompt: dict):
    return openai_client.chat.completions.create(
        model=settings.CHAT_MODEL,
        messages=[
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ],
        temperature=0.0,  # Reduce variation; model output still requires validation.
        max_tokens=2000,
        response_format={"type": "json_object"},
    )


def extract_document_data(
    request: ExtractionRequest, owner_id: str, db: Session
) -> ExtractionResponse:
    doc = get_document(db, request.document_id, owner_id)

    if doc.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document must be in 'ready' status to extract. Current status: {doc.status}",
        )

    file_path = UPLOAD_DIR / doc.filename
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical file not found on server",
        )

    document_text = extract_text_from_file(file_path, doc.file_type)

    if request.document_type not in EXTRACTION_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported document type: {request.document_type}",
        )

    prompt_fn, schema_class = EXTRACTION_CONFIG[request.document_type]
    response = _call_extraction_model(prompt_fn(document_text))
    raw_json = response.choices[0].message.content

    try:
        data_dict = json.loads(_clean_json_response(raw_json))
        if not isinstance(data_dict, dict):
            raise ValueError("Expected a JSON object")
        confidence = data_dict.pop("confidence_score", None)
        if confidence is not None:
            confidence = float(confidence)
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("confidence_score must be between 0 and 1")
        validated_data = schema_class.model_validate(data_dict)
    except (ValueError, TypeError, AttributeError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Model returned data that didn't match the expected schema: {e}",
        ) from e

    extraction = Extraction(
        document_id=request.document_id,
        document_type=request.document_type.value,
        extracted_data=validated_data.model_dump(),
        confidence_score=confidence,
        model_used=settings.CHAT_MODEL,
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)

    return ExtractionResponse.model_validate(extraction)


def get_extraction(extraction_id: str, owner_id: str, db: Session) -> ExtractionResponse:
    extraction = (
        db.query(Extraction)
        .join(Document, Document.id == Extraction.document_id)
        .filter(Extraction.id == extraction_id, Document.owner_id == owner_id)
        .first()
    )
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction not found or access denied",
        )
    return ExtractionResponse.model_validate(extraction)


def list_extractions_for_document(document_id: str, owner_id: str, db: Session) -> list:
    get_document(db, document_id, owner_id)  # Raises 404 if not owned by this user

    extractions = (
        db.query(Extraction)
        .filter(Extraction.document_id == document_id)
        .order_by(Extraction.created_at.desc())
        .all()
    )
    return [ExtractionResponse.model_validate(e) for e in extractions]
