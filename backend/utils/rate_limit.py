"""Request rate limiting, keyed by client IP.

Auth endpoints get a tighter limit (see config.RATE_LIMIT_AUTH) to slow down
credential-stuffing and brute-force attempts; everything else uses the more
permissive default.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    strategy="fixed-window",
)
