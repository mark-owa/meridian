"""AI lead qualification, scoring, and outreach email drafting."""

import json
import logging
import re

from fastapi import HTTPException, status
from openai import OpenAI
from sqlalchemy import func
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings
from models.database import Lead
from models.schemas import (
    LeadCreate,
    LeadEmailDraft,
    LeadListResponse,
    LeadQualificationResult,
    LeadResponse,
)
from utils.prompts import lead_email_draft_prompt, lead_qualification_prompt
from utils.time import utcnow

settings = get_settings()
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger(__name__)


def _clean_json(raw: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    return re.sub(r"\s*```$", "", cleaned).strip()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=8))
def _call_model(prompt: dict, model: str, temperature: float, max_tokens: int):
    return openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )


def create_lead(lead_data: LeadCreate, owner_id: str, db: Session) -> Lead:
    """Create a lead record. Qualification is a separate step (POST .../qualify)
    so a rep can review or correct lead data before the model scores it."""
    lead = Lead(
        owner_id=owner_id,
        company_name=lead_data.company_name,
        contact_name=lead_data.contact_name,
        contact_email=lead_data.contact_email.lower(),
        industry=lead_data.industry,
        company_size=lead_data.company_size.value if lead_data.company_size else None,
        annual_revenue=lead_data.annual_revenue,
        budget_range=lead_data.budget_range,
        pain_points=lead_data.pain_points,
        source=lead_data.source.value if lead_data.source else None,
        notes=lead_data.notes,
        status="new",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def qualify_lead(lead_id: str, owner_id: str, db: Session) -> LeadResponse:
    """Score a lead and draft an outreach email in two model calls."""
    lead = _get_lead(db, lead_id, owner_id)

    lead_dict = {
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "contact_email": lead.contact_email,
        "industry": lead.industry,
        "company_size": lead.company_size,
        "annual_revenue": lead.annual_revenue,
        "budget_range": lead.budget_range,
        "pain_points": lead.pain_points,
        "source": lead.source,
        "notes": lead.notes,
    }

    qual_response = _call_model(
        lead_qualification_prompt(lead_dict), settings.CHAT_MODEL, temperature=0.2, max_tokens=1000
    )
    try:
        qual_dict = json.loads(_clean_json(qual_response.choices[0].message.content))
        qualification = LeadQualificationResult.model_validate(qual_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Lead qualification response failed validation: {e}",
        ) from e

    # A fast, cheaper model is plenty for email copy — save the flagship
    # model's budget for the reasoning-heavy qualification call above.
    try:
        email_response = _call_model(
            lead_email_draft_prompt(lead_dict, qual_dict),
            settings.FAST_MODEL,
            temperature=0.7,
            max_tokens=600,
        )
        email_dict = json.loads(_clean_json(email_response.choices[0].message.content))
        email_draft = LeadEmailDraft.model_validate(email_dict)
    except Exception:
        # Non-critical: qualification already succeeded, so don't fail the
        # whole request over a malformed draft or unavailable email model.
        logger.exception("Email drafting failed for lead %s", lead.id)
        email_draft = LeadEmailDraft(
            subject=f"Following up on {lead.company_name}",
            body="Email draft failed to generate. Please write manually.",
            tone="professional",
        )

    lead.qualification_score = qualification.score
    lead.qualification_reason = qualification.reasoning
    lead.recommended_action = qualification.recommended_action.value
    lead.strengths = qualification.strengths
    lead.concerns = qualification.concerns
    lead.drafted_email = email_draft.body
    lead.email_subject = email_draft.subject
    lead.status = "qualified"
    lead.qualified_at = utcnow()

    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)


def batch_qualify_leads(owner_id: str, db: Session, limit: int = 10) -> list[LeadResponse]:
    """Qualify up to `limit` unqualified leads. Capped because each lead
    costs two model calls — larger batches belong in a background job."""
    unqualified = (
        db.query(Lead)
        .filter(Lead.owner_id == owner_id, Lead.status == "new")
        .limit(limit)
        .all()
    )

    results = []
    for lead in unqualified:
        lead_id = lead.id
        try:
            results.append(qualify_lead(lead_id, owner_id, db))
        except Exception:
            db.rollback()
            logger.exception("Failed to qualify lead %s; continuing with remaining batch", lead_id)
            continue
    return results


def get_leads(
    owner_id: str,
    db: Session,
    status: str | None = None,
    min_score: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> LeadListResponse:
    query = db.query(Lead).filter(Lead.owner_id == owner_id)
    if status:
        query = query.filter(Lead.status == status)
    if min_score is not None:
        query = query.filter(Lead.qualification_score >= min_score)

    total = query.count()
    leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()

    qualified_count = (
        db.query(func.count(Lead.id))
        .filter(Lead.owner_id == owner_id, Lead.status == "qualified")
        .scalar() or 0
    )
    avg_score_result = (
        db.query(func.avg(Lead.qualification_score))
        .filter(Lead.owner_id == owner_id, Lead.qualification_score.isnot(None))
        .scalar()
    )

    return LeadListResponse(
        leads=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        qualified_count=qualified_count,
        avg_score=round(float(avg_score_result), 1) if avg_score_result is not None else None,
    )


def update_lead_status(lead_id: str, new_status: str, owner_id: str, db: Session) -> LeadResponse:
    valid_statuses = ["new", "qualified", "contacted", "converted", "lost"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    lead = _get_lead(db, lead_id, owner_id)
    lead.status = new_status
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)


def delete_lead(lead_id: str, owner_id: str, db: Session) -> None:
    lead = _get_lead(db, lead_id, owner_id)
    db.delete(lead)
    db.commit()


def _get_lead(db: Session, lead_id: str, owner_id: str) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.owner_id == owner_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found or access denied",
        )
    return lead
