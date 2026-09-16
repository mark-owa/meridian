"""Timezone helpers.

datetime.utcnow() is deprecated as of Python 3.12. This keeps the same
naive-UTC semantics (so it's a drop-in replacement for every existing
DateTime column and JWT claim in this codebase) without the deprecation
warning that datetime.utcnow() now emits on every call.
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
