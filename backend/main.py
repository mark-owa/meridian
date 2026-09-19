"""Meridian API entry point."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from api.routes import analytics, auth, documents, extraction, knowledge, leads
from config import get_settings
from models.database import engine
from utils.logging import configure_logging
from utils.rate_limit import limiter

settings = get_settings()

configure_logging(settings.ENVIRONMENT)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production_readiness()
    logger.info("Meridian API started (environment=%s)", settings.ENVIRONMENT)
    yield
    logger.info("Meridian API shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Unified API for knowledge retrieval, document intelligence, and lead qualification.",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """Attach a request ID to every request/response pair and log timing.
    The ID is echoed back in the response header so a client-reported bug
    can be traced to the exact server-side log line."""
    request_id = str(uuid.uuid4())
    start = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s -> %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a stable, predictable error shape instead of FastAPI's default
    raw Pydantic error dump, which varies in structure across error types."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "detail": [
                {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]}
                for err in exc.errors()
            ],
        },
    )


@app.get("/health", tags=["System"])
def liveness():
    """Liveness probe: is the process up? Doesn't touch the database."""
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health/ready", tags=["System"])
def readiness():
    """Readiness probe: can this instance actually serve traffic? Checked
    separately from liveness so an orchestrator doesn't restart a healthy
    process just because its database connection is briefly down."""
    checks = {"database": False}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error("Readiness check failed: database unreachable: %s", e)

    all_ready = all(checks.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if all_ready else "not_ready", "checks": checks},
    )


api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)
app.include_router(knowledge.router, prefix=api_prefix)
app.include_router(extraction.router, prefix=api_prefix)
app.include_router(leads.router, prefix=api_prefix)
app.include_router(analytics.router, prefix=api_prefix)
