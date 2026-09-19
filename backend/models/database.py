"""SQLAlchemy ORM models and session management."""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import get_settings
from utils.time import utcnow

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    company = Column(String, nullable=True)
    role = Column(String, default="user")  # admin | user | viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="owner", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_owner_status", "owner_id", "status"),
        Index("ix_documents_owner_created", "owner_id", "created_at"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending -> processing -> ready | failed
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    processed_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="documents")
    extractions = relationship("Extraction", back_populates="document", cascade="all, delete-orphan")


class Extraction(Base):
    __tablename__ = "extractions"
    __table_args__ = (
        Index("ix_extractions_document", "document_id"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    document_type = Column(String, nullable=False)  # invoice | contract | receipt
    extracted_data = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=True)
    model_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    document = relationship("Document", back_populates="extractions")


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_owner_status", "owner_id", "status"),
        Index("ix_leads_owner_score", "owner_id", "qualification_score"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    company_name = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    annual_revenue = Column(String, nullable=True)
    budget_range = Column(String, nullable=True)
    pain_points = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    qualification_score = Column(Integer, nullable=True)
    qualification_reason = Column(Text, nullable=True)
    recommended_action = Column(String, nullable=True)
    strengths = Column(JSON, nullable=True)
    concerns = Column(JSON, nullable=True)
    drafted_email = Column(Text, nullable=True)
    email_subject = Column(String, nullable=True)

    status = Column(String, default="new")  # new -> qualified -> contacted -> converted | lost
    created_at = Column(DateTime, default=utcnow)
    qualified_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="leads")


class QueryLog(Base):
    __tablename__ = "query_logs"
    __table_args__ = (
        Index("ix_query_logs_user_created", "user_id", "created_at"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    sources_used = Column(JSON, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
