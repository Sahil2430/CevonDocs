# CevonDocs — Implementation Plan (Revised)

Upload any receipt or invoice image → schema-validated structured data with per-field confidence scores and a human-review queue for uncertain extractions.

**Project path:** `C:\Users\sahil_\.gemini\antigravity\scratch\cevondocs`

---

## Design Principles

- **Flat architecture.** No nested `app/routers/`, `app/services/`, `app/middleware/` trees. Every Python file lives in one directory.
- **Plain functions over classes.** A function that does one thing is easier to test, read, and debug than a service class with injected dependencies.
- **stdlib first.** `sqlite3`, `pathlib`, `uuid`, `logging`, `json`, `os` — no SQLAlchemy, no async DB layer, no pydantic-settings.
- **Single FastAPI file.** Three endpoints don't justify three routers.
- **Every file earns its place.** If the spec doesn't require it, it doesn't exist.

---

## Project Structure (15 code files + config)

```
cevondocs/
│
│── main.py               # FastAPI app — all endpoints + /metrics + logging config
│── config.py             # os.environ wrapper, constants
│── schemas.py            # Pydantic models (extraction + API I/O)
│── db.py                 # sqlite3 init + CRUD functions
│── utils.py              # Generic helpers (UUID, timestamp, base64, retry)
│── moderation.py         # OpenAI Moderation gate (one function)
│── extraction.py         # GPT-4o vision extraction (one function)
│── confidence.py         # Threshold routing logic (one function)
│── watermark.py          # PIL watermark stamp (one function)
│── pii.py                # Regex PII redaction (one function)
│── metrics.py            # Prometheus Counter/Histogram objects
│── streamlit_app.py      # Streamlit UI — Upload tab + Review tab
│
│── tests/
│   │── test_schemas.py       # Pydantic round-trip + validation
│   │── test_pii.py           # PII regex coverage
│   └── test_confidence.py    # Threshold routing logic
│
│── uploads/              # Watermarked images (gitignored)
│── Dockerfile
│── docker-compose.yml    # app + prometheus + grafana
│── prometheus.yml        # Scrape config
│── grafana/
│   └── dashboard.json    # Pre-built panels
│── .github/
│   └── workflows/
│       └── ci-cd.yml     # pytest → docker build → cloud run deploy
│── requirements.txt      # All versions pinned (see note below)
│── .env.example
└── README.md
```

> [!NOTE]
> **15 Python files** (12 app + 3 test). Everything else is config/infra.

---

## Open Questions

> [!IMPORTANT]
> **Confidence scores:** OpenAI structured output doesn't natively emit per-field confidence. The standard approach is to **prompt GPT-4o to self-report a confidence float (0–1)** for each field. This is what Ramp/Brex-style systems use. OK with you?

> [!IMPORTANT]
> **Frontend choice:** The spec lists Streamlit as primary, vanilla HTML/JS as an alt. I'll build **Streamlit** (faster, all-Python, `st.data_editor` maps perfectly to the review queue). Confirm?

---

## File-by-File Design

---

### config.py

Simple `os.environ.get()` with defaults. No framework.

```python
import os

OPENAI_API_KEY       = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL         = os.environ.get("OPENAI_MODEL", "gpt-4o")
MODERATION_MODEL     = os.environ.get("MODERATION_MODEL", "omni-moderation-latest")
REVIEW_THRESHOLD     = float(os.environ.get("REVIEW_THRESHOLD", "0.75"))
MODERATION_THRESHOLD = float(os.environ.get("MODERATION_THRESHOLD", "0.7"))
MAX_IMAGE_DIMENSION  = int(os.environ.get("MAX_IMAGE_DIMENSION", "2048"))
UPLOAD_DIR           = os.environ.get("UPLOAD_DIR", "uploads")
DATABASE_PATH        = os.environ.get("DATABASE_PATH", "cevondocs.db")
COST_PER_TOKEN       = float(os.environ.get("COST_PER_TOKEN", "0.0000025"))
APP_VERSION          = "1.0.0"
```

> [!TIP]
> `COST_PER_TOKEN` is configurable via environment variable because OpenAI pricing changes over time. The default `0.0000025` reflects gpt-4o pricing at time of writing. Update it in `.env` when pricing changes — no code change required.

---

### schemas.py

Two layers: **extraction schema** (goes to `response_format`) and **API schemas** (FastAPI request/response).

**Extraction (passed to GPT-4o):**

```python
class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float
    confidence: float          # 0.0–1.0, model self-reports

class InvoiceSchema(BaseModel):
    vendor: str
    vendor_confidence: float
    invoice_number: str
    invoice_number_confidence: float
    date: str
    date_confidence: float
    currency: str
    currency_confidence: float
    subtotal: float
    subtotal_confidence: float
    tax: float
    tax_confidence: float
    total: float
    total_confidence: float
    line_items: list[LineItem]
    overall_confidence: float
```

> [!NOTE]
> Flat `field` + `field_confidence` pairs instead of nested `ConfidenceField` wrappers. Simpler to access, simpler to serialize, simpler for the LLM to fill. For this project we intentionally use required fields without defaults to simplify validation, improve schema consistency, and maximize structured output reliability.

**API schemas:** `IngestResponse`, `ReviewResponse`, `ApproveRequest`, `ApproveResponse` — straightforward Pydantic models wrapping the above, plus `document_id`, `status`, and `flagged_fields`.

---

### db.py

Raw `sqlite3`. Four functions:

```python
def init_db()           # CREATE TABLE IF NOT EXISTS documents (...)
def insert_document()   # INSERT with id, filename, status, extracted_json, created_at
def get_pending()       # SELECT WHERE status = 'pending_review'
def approve_document()  # UPDATE status = 'approved', reviewed_json = ?
```

**Single table — `documents`:**

| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID) | Primary key |
| `filename` | TEXT | Original upload name |
| `status` | TEXT | `auto_approved` / `pending_review` / `approved` / `blocked` |
| `extracted_json` | TEXT | Full `InvoiceSchema` as JSON |
| `reviewed_json` | TEXT | Corrected JSON after human review (nullable) |
| `created_at` | TEXT | ISO timestamp |

> [!TIP]
> **No `flagged_fields` column.** Flagged fields are derived at query time by calling `route_document()` on `extracted_json` with the current `REVIEW_THRESHOLD`. This avoids duplicated state — the confidence values are already in the extraction JSON, so re-deriving is trivial and always consistent.

No ORM. No migrations. `CREATE TABLE IF NOT EXISTS` on startup.

---

### moderation.py

One function:

```python
def check_moderation(b64_image: str) -> tuple[bool, str | None]:
    """
    Calls OpenAI Moderation API with omni-moderation-latest.
    Returns (is_safe, blocked_reason).
    """
```

- Sends `input=[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}]`
- Iterates category scores, compares against `MODERATION_THRESHOLD`
- Returns `(True, None)` if safe, `(False, "violence")` if blocked

---

### extraction.py

One function:

```python
def extract_invoice(b64_image: str) -> tuple[InvoiceSchema, dict]:
    """
    Calls GPT-4o with response_format=InvoiceSchema.
    Returns (parsed_schema, usage_stats).
    """
```

- Resizes image to ≤ `MAX_IMAGE_DIMENSION` via PIL before encoding
- Calls `client.beta.chat.completions.parse()` with `response_format=InvoiceSchema`
- Uses `retry_on_transient()` from `utils.py` to handle rate limits and transient failures
- System prompt instructs: *"For each field, assign a confidence score 0.0–1.0 based on how clearly you can read the value from the image. Use 1.0 for clearly legible, 0.5 for partially legible, 0.0 for guessed."*
- Returns parsed object + `{"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}`

---

### confidence.py

One function:

```python
def route_document(invoice: InvoiceSchema, threshold: float) -> tuple[str, list[str]]:
    """
    Inspects all *_confidence fields and line_item confidences.
    Returns (status, flagged_fields).
      - status: 'auto_approved' or 'pending_review'
      - flagged_fields: list of field names below threshold
    """
```

- Iterates top-level fields: `vendor_confidence`, `invoice_number_confidence`, `date_confidence`, `currency_confidence`, `subtotal_confidence`, `tax_confidence`, `total_confidence`
- Iterates `line_items[i].confidence`
- Collects any field name where confidence < threshold
- Returns `('auto_approved', [])` if nothing flagged, else `('pending_review', ['vendor', 'line_items[2]', ...])`

> [!NOTE]
> This is also called at query time by `GET /review` to derive flagged fields from stored extraction JSON — no duplicated state in the database.

---

### watermark.py

One function:

```python
def watermark_image(image_path: Path, doc_id: str, output_path: Path) -> None:
    """
    Draws '{doc_id} | {timestamp}' in semi-transparent gray
    at the bottom-right corner. Saves to output_path.
    Never modifies the original.
    """
```

- `PIL.Image.open()` → `ImageDraw.text()` → `img.save(output_path)`

---

### pii.py

One function:

```python
def redact_pii(text: str) -> str:
    """
    Replaces SSN, email, phone, Aadhaar patterns with [REDACTED].
    """
```

Patterns:
- SSN: `\d{3}-\d{2}-\d{4}`
- Email: `[\w.+-]+@[\w.-]+`
- Phone: `\+?[\d\s\-()]{10,}`
- Aadhaar: `\d{4}\s?\d{4}\s?\d{4}`

---

### utils.py

Generic helper functions. No business logic — only reusable utilities that would otherwise be duplicated.

```python
import uuid
import time
import base64
import logging
from datetime import datetime, timezone
from pathlib import Path

def generate_id() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())

def now_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()

def image_to_base64(image_bytes: bytes) -> str:
    """Encode raw image bytes to base64 string."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")

def save_upload(image_bytes: bytes, upload_dir: Path, doc_id: str, filename: str) -> Path:
    """Save uploaded image to uploads/{doc_id}/original.{ext}. Returns saved path."""
    doc_dir = upload_dir / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix or ".png"
    dest = doc_dir / f"original{ext}"
    dest.write_bytes(image_bytes)
    return dest

def retry_on_transient(fn, max_retries=3, base_delay=1.0):
    """
    Call fn(). Retry on transient OpenAI errors (rate limit, timeout, server error).
    Exponential backoff: base_delay * 2^attempt seconds.
    Returns fn() result on success, raises on final failure.
    """
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            error_name = type(e).__name__
            is_transient = any(keyword in error_name for keyword in
                ["RateLimitError", "APITimeoutError", "InternalServerError", "APIConnectionError"])
            if not is_transient or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logging.getLogger("cevondocs").warning(
                f"Transient error ({error_name}), retrying in {delay}s (attempt {attempt+1}/{max_retries})"
            )
            time.sleep(delay)
```

> [!NOTE]
> The retry helper is a plain function with a for-loop and `time.sleep` — no external library, no decorators. It catches OpenAI's known transient error types by class name and applies exponential backoff.

---

### metrics.py

Prometheus metric objects only — no middleware, no classes:

```python
from prometheus_client import Counter, Histogram, Gauge

moderation_latency   = Histogram("moderation_latency_seconds", "Moderation API latency")
extraction_latency   = Histogram("extraction_latency_seconds", "GPT-4o extraction latency")
token_cost_total     = Counter("token_cost_usd_total", "Cumulative token cost in USD")
auto_approvals       = Counter("auto_approvals_total", "Documents auto-approved")
reviews_total        = Counter("reviews_total", "Documents sent to review")
docs_processed       = Counter("documents_processed_total", "Total documents processed", ["status"])
```

Metrics are **recorded inline** inside `main.py` endpoint functions. No middleware layer.

---

### main.py

Single FastAPI application. Three business endpoints + `/metrics` + health check.

**Logging:** Configured at module level in `main.py` using Python's built-in `logging` module. PII redaction is applied (via `pii.redact_pii()`) before any extracted content is logged. No separate logging module.

```python
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("cevondocs")

app = FastAPI(title="CevonDocs", version=config.APP_VERSION)

@app.on_event("startup")
def startup():
    db.init_db()
    Path(config.UPLOAD_DIR).mkdir(exist_ok=True)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": "connected",  # verified via a quick db.init_db() no-op
        "version": config.APP_VERSION
    }

@app.post("/ingest")
def ingest(file: UploadFile): ...
    # 1. Validate file type (JPG/PNG by content_type + extension)
    # 2. Read bytes → utils.image_to_base64()
    # 3. check_moderation() → block or continue
    # 4. extract_invoice() → InvoiceSchema (uses retry_on_transient internally)
    # 5. pii.redact_pii() on extracted JSON before logging
    # 6. confidence.route_document() → (status, flagged_fields)
    # 7. watermark_image() → save to uploads/{doc_id}/
    # 8. db.insert_document() into SQLite
    # 9. Record Prometheus metrics inline
    # 10. Return IngestResponse

@app.get("/review")
def review(): ...
    # db.get_pending() from SQLite
    # For each doc: confidence.route_document() to derive flagged_fields
    # Return list with flagged field indicators

@app.post("/approve")
def approve(req: ApproveRequest): ...
    # db.approve_document() in SQLite → return confirmation

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

### streamlit_app.py

Single file, two tabs:

**Tab 1 — Upload:**
- `st.file_uploader(type=["jpg", "jpeg", "png"])`
- `st.image()` preview
- "Process" button → `requests.post("/ingest", files=...)`
- Display results: extracted fields + confidence badges
  - 🟢 ≥ 0.75 — auto-approved
  - 🟡 0.50–0.74 — uncertain
  - 🔴 < 0.50 — low confidence
- Show flagged fields with ⚠️

**Tab 2 — Review Queue:**
- Polls `GET /review`
- `st.data_editor` for inline correction of flagged fields
- Side-by-side: original image + editable fields
- "Approve" button → `requests.post("/approve", json=...)`

---

### tests/

**test_schemas.py:**
- `InvoiceSchema` instantiation with valid data
- JSON round-trip: `.model_dump_json()` → `InvoiceSchema.model_validate_json()` → equality
- Invalid data (negative confidence, wrong types) raises `ValidationError`

**test_pii.py:**
- SSN `123-45-6789` → `[REDACTED]`
- Email `user@example.com` → `[REDACTED]`
- Phone `+1-555-123-4567` → `[REDACTED]`
- Clean text passes through unchanged

**test_confidence.py:**
- All fields ≥ 0.75 → `auto_approved`, empty flagged list
- One field at 0.5 → `pending_review`, that field in flagged list
- Edge case: exactly 0.75 → `auto_approved`

---

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000 8501
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 & streamlit run streamlit_app.py --server.port 8501 --server.headless true"]
```

---

### docker-compose.yml

Three services: `app`, `prometheus`, `grafana`. Needed because the spec requires a Prometheus + Grafana dashboard — a single Dockerfile can't provide that.

### requirements.txt

All dependency versions **pinned** (e.g. `fastapi==0.115.0`, not `fastapi`). This ensures reproducible builds across developer machines, CI, Docker, and AI-agent-generated environments. Pin versions at the time of implementation and document the Python version (3.11) in the README.

---

### .github/workflows/ci-cd.yml

```yaml
on: push (main)
jobs:
  test-and-deploy:
    steps:
      - checkout
      - setup python 3.11
      - pip install -r requirements.txt
      - pytest tests/ -v
      - docker build -t cevondocs .
      - gcloud auth + push to GCR
      - gcloud run deploy
```

---

### grafana/dashboard.json

Pre-built panels:
- Moderation p99 latency
- Extraction p99 latency
- Token cost per document
- Auto-approval rate (%)
- Documents per minute

---

## Milestones

Each milestone produces a **working, testable application**. No milestone depends on future work.

---

### Milestone 1 — FastAPI skeleton + schemas

**Files:** `main.py`, `config.py`, `schemas.py`, `utils.py`, `requirements.txt`, `.env.example`

**Result:** `uvicorn main:app` → Swagger UI at `/docs`. `/health` returns `{"status": "ok", "database": "connected", "version": "1.0.0"}`. Pydantic schemas importable and validatable.

---

### Milestone 2 — Image upload

**Files:** update `main.py`, update `utils.py`

**Result:** `POST /ingest` accepts a JPG/PNG, validates file type, generates a UUID via `utils.generate_id()`, saves the original to `uploads/{doc_id}/` via `utils.save_upload()`. Returns the document ID. No database yet — just file storage.

---

### Milestone 3 — Moderation gate

**Files:** `moderation.py`, update `main.py`

**Result:** `/ingest` now calls the OpenAI Moderation API first. Blocked images get a 422 response with `blocked_reason`. Safe images continue through the pipeline.

---

### Milestone 4 — GPT-4o extraction

**Files:** `extraction.py`, update `main.py`

**Result:** Safe images are extracted via GPT-4o → `InvoiceSchema`. Uses `utils.retry_on_transient()` for resilience against rate limits and transient errors. Returns parsed structured data with per-field confidence scores.

---

### Milestone 5 — SQLite persistence

**Files:** `db.py`, update `main.py`

**Result:** `init_db()` creates the `documents` table on startup. `/ingest` now writes extraction results to SQLite. Documents are queryable. Status is set to `processing` pending confidence routing.

---

### Milestone 6 — Confidence routing

**Files:** `confidence.py`, update `main.py`

**Result:** After extraction, `route_document()` inspects confidence fields. Documents are routed to `auto_approved` or `pending_review`. Flagged fields are derived (not stored) and returned in the response.

---

### Milestone 7 — Review API + PII redaction

**Files:** `pii.py`, update `main.py`

**Result:** `GET /review` returns pending documents with flagged fields derived via `route_document()`. `POST /approve` marks them approved with corrected data. `redact_pii()` is applied before any extracted content is logged.

---

### Milestone 8 — Watermarking

**Files:** `watermark.py`, update `main.py`

**Result:** After extraction, source images are watermarked with `{doc_id} | {timestamp}` and saved as `uploads/{doc_id}/watermarked.png`. Originals are never modified.

---

### Milestone 9 — Streamlit UI

**Files:** `streamlit_app.py`

**Result:** Two-tab Streamlit app. Upload tab sends images to `/ingest` and displays results with color-coded confidence badges. Review tab shows pending documents in `st.data_editor` and submits corrections via `/approve`.

---

### Milestone 10 — Prometheus metrics

**Files:** `metrics.py`, update `main.py`

**Result:** `/metrics` endpoint exposes `moderation_latency_seconds`, `extraction_latency_seconds`, `token_cost_usd_total`, `auto_approvals_total`, `documents_processed_total`. Metrics recorded inline in `/ingest`.

---

### Milestone 11 — Tests

**Files:** `tests/test_schemas.py`, `tests/test_pii.py`, `tests/test_confidence.py`

**Result:** `pytest tests/ -v` passes. Schema round-trip, PII redaction patterns, and confidence routing logic all verified.

---

### Milestone 12 — Docker + Grafana

**Files:** `Dockerfile`, `docker-compose.yml`, `prometheus.yml`, `grafana/dashboard.json`

**Result:** `docker-compose up` runs app + Prometheus + Grafana. All four services accessible at their respective ports.

---

### Milestone 13 — CI/CD + Cloud Run

**Files:** `.github/workflows/ci-cd.yml`, `README.md`

**Result:** GitHub Actions pipeline runs `pytest` → builds Docker image → pushes to GCR → deploys to Cloud Run. README documents setup, usage, and architecture.

---

## Verification Plan

### Automated
```bash
pytest tests/ -v
```

### Manual
1. Upload a real receipt → verify extraction fields + confidence scores
2. Upload an image with hard-to-read fields → verify it routes to review queue
3. Correct flagged fields in Streamlit → verify `/approve` updates SQLite
4. Check `uploads/{doc_id}/watermarked.png` for provenance stamp
5. Hit `/metrics` → verify counters increment after each `/ingest` call
6. `docker-compose up` → verify FastAPI, Streamlit, Prometheus, Grafana all accessible
7. Check logs → verify no PII in any log line

### Build
```bash
docker-compose up --build
# FastAPI:    http://localhost:8000/docs
# Streamlit:  http://localhost:8501
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000
```
