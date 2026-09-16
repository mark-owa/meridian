# Architecture

## Data and ownership

The SQLAlchemy model has five tables:

| Table | Purpose and ownership |
| --- | --- |
| `users` | Login credentials and profile data |
| `documents` | File metadata, owner, processing state, and chunk count |
| `extractions` | Validated model output; ownership follows the linked document |
| `leads` | Contact data, owner, qualification result, and manually editable status |
| `query_logs` | Questions, answers, retrieved source references, and user ID |

Service queries filter by the authenticated user's ID. Requests for another
user's document, extraction, or lead return `404`. Each vector chunk also carries
an `owner_id`; retrieval, deletion, and statistics filter by that owner. JWTs
identify the user, and the API checks the stored account on each protected request.

PostgreSQL is used in Compose, and SQLite is supported for development and tests.
Alembic manages schema changes. Startup also calls `create_all()` to create missing
tables, which does not alter existing tables or record a migration version. Use
`alembic upgrade head` before starting a new local database. A database originally
created by `create_all()` must be checked against the initial migration before
stamping its revision; do not stamp an unknown schema blindly.

## Upload and background processing

1. Check the declared media type and stream the file to a generated filename,
   enforcing the byte limit. Validate the saved content: PDF signature, required
   DOCX ZIP members, or a complete UTF-8 decode for text.
2. Commit a `pending` document and publish its ID to Celery. Common write and
   enqueue failures remove the new file; database commit failures roll back.
3. The worker records `processing`, extracts text, chunks it using the configured
   size/overlap, and generates embeddings. Ready documents skip repeat processing.
4. Successful indexing records `ready`, a chunk count, and a timestamp. Empty text
   records `failed`. Exceptions have up to two retries at a fixed 15-second delay.
5. After exhausted retries, the failure hook attempts vector cleanup and records
   a generic error for the user. A vector cleanup failure is logged independently
   so it does not prevent the database failure update.

The interface polls while documents are pending or processing. The upload response
represents the initial pending state, even when an eager test task has already
completed; fetch the document again for its final state.

API and worker use one **Chroma server** in Compose and the documented local setup.
Separate embedded clients can see updated SQL metadata while querying stale vector
indexes, so sharing the embedded directory across processes is unsupported. Tests
use an embedded client because all processing runs in one process.

The stores and queue are not transactionally coordinated. An API crash between
commit and queue publication can strand a pending document. Worker termination,
concurrent deletion, duplicate delivery, or an unavailable store can require manual
recovery. Late acknowledgements are enabled, but they do not guarantee recovery
from every worker crash or hard time limit. The supplied Redis service has no
persistent queue volume. There is no automatic cross-store reconciliation service.

## AI workflows

**Knowledge search:** embed a question, filter vector results by owner and optional
document IDs, and apply a similarity threshold. An empty collection or explicitly
empty selection returns no results without embedding the question. Retrieved
excerpts are sent to the chat model with instructions to cite them. Both generated
answers and no-match answers are logged. Source references and the prompt do not
guarantee grounded or correct output; users must check the excerpts.

**Structured extraction:** require a ready document and read its file again. Prompt
for invoice, contract, or receipt JSON; validate the object, finite confidence in
`[0, 1]`, and the relevant Pydantic schema before saving. Malformed output returns
`422`. Optional schema fields may be null; schema validity is not semantic accuracy.
`general` exists as a document/chunking category but is not an extraction schema.

**Lead qualification:** call the chat model for a score, reasoning, and recommended
action, then call the email model for a draft. Draft parsing or model-call failure
uses a manual-writing placeholder and preserves a successful qualification. A
batch rolls back an individual failed transaction before continuing. Qualification
sets the status to `qualified`; manual status changes accept any supported label,
so this is not an enforced sales state machine. Requalification can reset a later
manual status. Drafts are stored, never sent.

## Security and operational scope

- Passwords use Argon2id. Login verifies a dummy hash for nonexistent accounts to
  reduce timing differences; it does not guarantee identical response timing.
- JWT decoding uses the configured algorithm explicitly. Account activity is
  checked on each authenticated request.
- SlowAPI applies IP-based default limits, with tighter registration/login limits.
  Use Redis-backed rate-limit storage across API processes. Proxy configuration
  matters because the source IP determines the rate-limit key.
- Production startup guards signing keys, API-key presence, and wildcard CORS.
  They do not verify external-service connectivity or model availability.
- `/health` checks the API process; `/health/ready` checks only SQL connectivity.
  Neither verifies the worker, Redis, Chroma, or OpenAI.
- PDF signatures and DOCX container checks are basic format checks, not antivirus
  scanning or complete structural validation. Scanned PDFs and DOCX tables are
  outside the current extractor's scope.
- Tokens live in browser local storage. There is no password reset, refresh-token
  flow, complete role policy, team sharing, billing, or usage metering.

## Verification scope

The backend suite uses SQLite, real local Chroma, synchronous Celery execution,
and mocked AI output. Tests cover authentication, document ownership and ingestion,
retrieval, extraction validation, lead behavior, upload cleanup, UTF-8 boundaries,
chunk budgets, and exhausted worker failures. Frontend verification uses TypeScript,
ESLint, and a production build. These checks do not substitute for a live OpenAI
integration test or a PostgreSQL/Redis/Docker deployment test.
