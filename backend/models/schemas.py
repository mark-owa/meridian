"""Pydantic request/response schemas.

Route handlers never return SQLAlchemy models directly — everything is
shaped through a schema here first, so internal columns (password hashes,
etc.) can never leak into an API response by accident.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"


class DocumentStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class DocumentType(str, Enum):
    invoice = "invoice"
    contract = "contract"
    receipt = "receipt"
    general = "general"


class CompanySize(str, Enum):
    startup = "startup"
    smb = "smb"
    enterprise = "enterprise"


class LeadSource(str, Enum):
    website = "website"
    referral = "referral"
    cold_outreach = "cold_outreach"
    trade_show = "trade_show"
    social = "social"


class LeadAction(str, Enum):
    pursue = "pursue"
    nurture = "nurture"
    disqualify = "disqualify"


class LeadStatus(str, Enum):
    new = "new"
    qualified = "qualified"
    contacted = "contacted"
    converted = "converted"
    lost = "lost"


# Auth

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    company: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    company: str | None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Documents

class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatus
    chunk_count: int
    error_message: str | None
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# Knowledge / RAG

class KnowledgeQueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=1000)
    top_k: int | None = Field(None, ge=1, le=20)
    document_ids: list[str] | None = Field(
        None, description="Restrict search to specific documents. Omit to search all."
    )


class SourceChunk(BaseModel):
    document_id: str
    document_name: str
    chunk_text: str
    similarity_score: float
    chunk_index: int


class KnowledgeQueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[SourceChunk]
    tokens_used: int
    response_time_ms: int


# Extraction

class InvoiceLineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    total_price: float | None = None


class InvoiceData(BaseModel):
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    vendor_name: str | None = None
    vendor_address: str | None = None
    vendor_email: str | None = None
    client_name: str | None = None
    client_address: str | None = None
    line_items: list[InvoiceLineItem] = []
    subtotal: float | None = None
    tax_amount: float | None = None
    tax_rate: float | None = None
    total_amount: float | None = None
    currency: str | None = "USD"
    payment_terms: str | None = None
    notes: str | None = None


class ContractParty(BaseModel):
    name: str
    role: str
    address: str | None = None


class ContractData(BaseModel):
    contract_type: str | None = None
    effective_date: str | None = None
    expiration_date: str | None = None
    parties: list[ContractParty] = []
    key_obligations: list[str] = []
    payment_terms: str | None = None
    termination_clause: str | None = None
    governing_law: str | None = None
    key_risks: list[str] = []


class ReceiptData(BaseModel):
    merchant_name: str | None = None
    merchant_address: str | None = None
    transaction_date: str | None = None
    transaction_time: str | None = None
    items: list[InvoiceLineItem] = []
    subtotal: float | None = None
    tax_amount: float | None = None
    tip_amount: float | None = None
    total_amount: float | None = None
    payment_method: str | None = None
    receipt_number: str | None = None
    category: str | None = None


class ExtractionRequest(BaseModel):
    document_id: str
    document_type: DocumentType


class ExtractionResponse(BaseModel):
    id: str
    document_id: str
    document_type: str
    extracted_data: Any
    confidence_score: float | None
    model_used: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Leads

class LeadCreate(BaseModel):
    company_name: str = Field(..., min_length=2)
    contact_name: str = Field(..., min_length=2)
    contact_email: EmailStr
    industry: str | None = None
    company_size: CompanySize | None = None
    annual_revenue: str | None = None
    budget_range: str | None = None
    pain_points: str | None = None
    source: LeadSource | None = None
    notes: str | None = None


class LeadQualificationResult(BaseModel):
    score: int = Field(..., ge=0, le=100)
    reasoning: str
    recommended_action: LeadAction
    strengths: list[str]
    concerns: list[str]
    next_steps: list[str]


class LeadEmailDraft(BaseModel):
    subject: str
    body: str
    tone: str


class LeadResponse(BaseModel):
    id: str
    company_name: str
    contact_name: str
    contact_email: str
    industry: str | None
    company_size: str | None
    budget_range: str | None
    pain_points: str | None
    source: str | None
    qualification_score: int | None
    qualification_reason: str | None
    recommended_action: str | None
    strengths: list[str] | None
    concerns: list[str] | None
    drafted_email: str | None
    email_subject: str | None
    status: str
    created_at: datetime
    qualified_at: datetime | None

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    leads: list[LeadResponse]
    total: int
    qualified_count: int
    avg_score: float | None


# Analytics

class DashboardStats(BaseModel):
    total_documents: int
    documents_ready: int
    total_queries: int
    avg_response_time_ms: float | None
    total_leads: int
    qualified_leads: int
    avg_lead_score: float | None
    total_extractions: int


# Shared

class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    code: str | None = None
