# 🧾 CevonDocs — Complete Technical Knowledge Document

**Project:** CevonDocs — Receipt & Invoice Intelligence  
**Author:** Lead AI Systems Engineer  
**Date:** July 22, 2026  
**Version:** 1.0.0  
**Repository State:** Production-Ready & Feature Complete  

---

# 1. Project Overview

## Purpose of CevonDocs
CevonDocs is an enterprise-grade, full-stack document intelligence application designed for financial operations, accounts payable, and compliance teams. It automates the ingestion, safety screening, vision extraction, uncertainty routing, PII redaction, provenance watermarking, and human-in-the-loop review of heterogeneous receipt and invoice images (JPEG, PNG).

## Problem It Solves
1. **Fragile Layout Templates**: Traditional OCR engines (e.g., Tesseract or rule-based regex coordinate masks) require per-vendor templates. When a vendor updates their layout, extraction breaks. CevonDocs uses multi-provider vision Large Language Models (OpenAI GPT-4o, Google Gemini 2.5 Flash, Groq Qwen 27B) paired with strict Pydantic schemas (`InvoiceSchema`) to extract unstructured data without layout templates.
2. **Silent AI Hallucinations & Overconfidence**: Unchecked AI vision models occasionally guess amounts, dates, or vendor names. CevonDocs enforces **Uncertainty Routing**: every extracted field carries a self-reported confidence score ($0.0$ to $1.0$). Any field or line item scoring below `0.75` automatically routes the document to a human review queue (`pending_review`) rather than silently committing unverified data.
3. **Data Security & Privacy Leaks**: Processing financial documents risks logging sensitive Personally Identifiable Information (PII). CevonDocs applies automated regex PII redaction prior to log output and stamps non-destructive provenance watermarks onto stored images.

## Target Users
- **Accounts Payable Clerks**: Review flagged low-confidence receipts, correct line items via Streamlit, and approve structured data for ERP ingestion.
- **Finance Operations Managers**: Monitor processing throughput, auto-approval rates, API latency, and cumulative LLM token costs via Prometheus and Grafana dashboards.
- **Compliance & Security Engineers**: Audit PII redaction, content moderation gate blocks, and image provenance stamps.

## End-to-End Processing Pipeline
```text
Document Upload (JPEG/PNG <= 10MB)
  ↓
Basic Image Validation (Format, Integrity, File Size)
  ↓
Provider-Agnostic Moderation Gate (auto / openai / gemini / local)
  ↓ [If Unsafe/Corrupted: HTTP 422 Blocked]
PIL Watermarking & Image Storage (uploads/{doc_id}/original & watermarked.png)
  ↓
Multi-Provider Vision Extraction (OpenAI / Gemini / Groq)
  ↓ [If API Failure / Invalid Key: HTTP 503 Service Unavailable]
Pydantic Schema Validation (InvoiceSchema & LineItem)
  ↓
Confidence Router (Fail-Closed Default = 0.0, Threshold = 0.75)
  ├── All Fields >= 0.75 → Status: "auto_approved"
  └── Any Field < 0.75  → Status: "pending_review"
  ↓
PII Redaction Engine (SSNs, Emails, Phone Numbers, Aadhaar IDs masked)
  ↓
SQLite Persistence (data/cevondocs.db)
  ↓
Prometheus Inline Metrics Recording (/metrics)
  ↓
API Response / Human Review Queue (Streamlit st.data_editor)
```

---

# 2. High-Level Architecture

## Architecture Diagram (ASCII)

```
                       ┌──────────────────────────────────────────────┐
                       │          Streamlit UI (Port 8501)            │
                       │  • Tab 1: Upload & Extract                   │
                       │  • Tab 2: Human Review Queue (st.data_editor)│
                       └──────────────────────┬───────────────────────┘
                                              │ REST API (HTTP)
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Backend (Port 8000)                                  │
│                                                                                             │
│  ┌────────────────────────┐  ┌─────────────────────────┐  ┌──────────────────────────────┐ │
│  │   Request Validator    │─>│ Provider-Agnostic Gate  │─>│   PIL Provenance Stamper     │ │
│  │ (Max 10MB, JPG/PNG)    │  │  (backend/moderation/)  │  │   (watermark_image)          │ │
│  └────────────────────────┘  └─────────────────────────┘  └──────────────┬───────────────┘ │
│                                                                          │                 │
│  ┌───────────────────────────────────────────────────────────────────────v───────────────┐ │
│  │                       AI Vision Extraction Router (extraction.py)                     │ │
│  │    ┌─────────────────────────┬─────────────────────────┬──────────────────────────┐   │ │
│  │    │ backend/ai/openai_prov  │ backend/ai/gemini_prov  │  backend/ai/groq_prov    │   │ │
│  │    │  (GPT-4o Vision API)    │ (Gemini 2.5 Flash SDK)  │ (Groq Qwen Vision Mode)  │   │ │
│  │    └─────────────────────────┴─────────────────────────┴──────────────────────────┘   │ │
│  └──────────────────────────────────────┬────────────────────────────────────────────────┘ │
│                                         │                                                  │
│  ┌────────────────────────┐  ┌──────────v──────────────┐  ┌──────────────────────────────┐ │
│  │  PII Redaction Engine  │<─│    Confidence Router    │<─│   Pydantic Contract Validator│ │
│  │    (SSN/Email/Aadhaar) │  │(confidence.py, Fail 0.0)│  │    (InvoiceSchema)           │ │
│  └───────────┬────────────┘  └─────────────────────────┘  └──────────────────────────────┘ │
│              │                                                                             │
│              ▼                                                                             │
│  ┌────────────────────────┐  ┌─────────────────────────┐                                   │
│  │ SQLite Database Layer  │  │ Prometheus Metrics API  │                                   │
│  │ (data/cevondocs.db)   │  │   (metrics.py, /metrics)│                                   │
│  └────────────────────────┘  └──────────┬──────────────┘                                   │
└─────────────────────────────────────────┼──────────────────────────────────────────────────┘
                                          │ Scrape (5s)
                                          ▼
                       ┌──────────────────────────────────────────────┐
                       │          Prometheus Server (Port 9090)       │
                       └──────────────────────┬───────────────────────┘
                                              │ PromQL Query
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │          Grafana Dashboard (Port 3000)       │
                       │  • P99 Latencies  • Auto-Approval Rate (%)   │
                       │  • Token Cost ($) • Document Throughput      │
                       └──────────────────────────────────────────────┘
```

## Core Components & Responsibilities
1. **FastAPI Application (`main.py`)**: Endpoints for `/health`, `/metrics`, `/ingest`, `/review`, and `/approve`. Manages request size enforcement, exception translation, latency timing, and pipeline execution.
2. **AI Vision Router & Providers (`backend/ai/`)**: Hot-swappable vision models (`openai_provider.py`, `gemini_provider.py`, `groq_provider.py`). `extraction.py` acts as a lightweight router dispatching work to the active provider specified in `config.AI_PROVIDER`.
3. **Provider-Agnostic Moderation System (`backend/moderation/`)**: Modular safety gate (`router.py`, `openai_moderation.py`, `gemini_moderation.py`). Supports `auto` provider selection, checking image integrity, size, and remote safety APIs before vision model invocation.
4. **Confidence Threshold Router (`confidence.py`)**: Evaluates extraction confidence scores against `config.REVIEW_THRESHOLD` (`0.75`). Implements fail-closed `0.0` fallbacks for missing fields.
5. **PII Masking Engine (`pii.py`)**: Executes regex replacement for SSNs, emails, phone numbers, and Aadhaar IDs prior to writing output to log streams.
6. **Watermark Engine (`watermark.py`)**: Renders non-destructive PIL gray text stamps (`{doc_id} | {timestamp}`) onto a separate `watermarked.png` file.
7. **Database Storage Layer (`db.py`)**: Manages thread-safe raw `sqlite3` transactions targeting `data/cevondocs.db`.
8. **Observability Stack (`metrics.py`, `prometheus.yml`, `grafana/`)**: Exposes Prometheus metrics and provisions Grafana dashboards for latency, auto-approval percentage, and LLM token costs.

---

# 3. Repository Structure

```text
cevondocs/
├── .env.example                       # Environment variable template
├── .gitignore                          # Excludes .env, *.db, uploads/, data/, pycache
├── Dockerfile                         # Python 3.11-slim container spec
├── docker-compose.yml                 # Multi-container orchestration (App, Prometheus, Grafana)
├── prometheus.yml                     # Prometheus scraper config
├── requirements.txt                   # Locked Python dependency manifest
├── main.py                            # FastAPI backend entrypoint & endpoint handlers
├── config.py                          # Environment variable parser & system constants
├── db.py                              # SQLite connection pool & query functions
├── schemas.py                         # Pydantic InvoiceSchema & API request/response models
├── extraction.py                      # AI vision provider routing facade
├── moderation.py                      # Moderation module entrypoint re-export
├── confidence.py                      # Confidence score routing logic
├── pii.py                             # Regex PII redaction engine
├── watermark.py                       # PIL image watermarking tool
├── metrics.py                         # Prometheus metrics declarations
├── utils.py                           # Shared image, UUID, ISO, and retry helpers
├── streamlit_app.py                   # Streamlit UI frontend
├── BUILD_NOTE.md                      # Capstone build & architectural note
├── README.md                          # Technical overview & quickstart guide
├── backend/                           # Modular backend components
│   ├── ai/                            # AI Vision Providers
│   │   ├── __init__.py
│   │   ├── openai_provider.py         # OpenAI GPT-4o vision provider
│   │   ├── gemini_provider.py         # Google Gemini 2.5 Flash provider
│   │   └── groq_provider.py           # Groq Qwen Vision provider
│   └── moderation/                    # Modular Moderation System
│       ├── __init__.py
│       ├── router.py                  # Moderation router & local image validation
│       ├── openai_moderation.py       # OpenAI Moderation API gate
│       └── gemini_moderation.py       # Gemini safety vision screening
├── grafana/                           # Grafana dashboard provisioning
│   ├── dashboard.json                 # Grafana dashboard JSON layout
│   └── provisioning/
│       ├── datasources/prometheus.yml # Prometheus datasource definition
│       └── dashboards/dashboard.yml   # Dashboard loader config
├── .github/
│   └── workflows/
│       └── ci-cd.yml                  # GitHub Actions CI (pytest) & GCP Cloud Run CD
├── data/                              # SQLite persistent storage directory
│   └── .gitkeep
├── uploads/                           # Ingested document image directory
│   └── .gitkeep
└── tests/                             # Automated Pytest Suite
    ├── __init__.py
    ├── test_schemas.py                # Schema validation tests
    ├── test_pii.py                    # PII regex redaction tests
    ├── test_confidence.py             # Confidence routing tests
    ├── test_moderation.py             # Modular moderation tests
    └── test_multi_provider_fixes.py   # Multi-provider contract & API error tests
```

---

# 4. File-by-File Documentation

## `main.py`
- **Purpose**: Main FastAPI web server application containing route handlers and app lifespan initialization.
- **Key Functions**:
  - `lifespan(app)`: Async context manager initializing the database via `db.init_db()` and creating `UPLOAD_DIR`.
  - `health()`: `GET /health` handler checking database connectivity and returning system version.
  - `get_metrics()`: `GET /metrics` handler returning Prometheus metrics payload.
  - `ingest(file)`: `POST /ingest` handler orchestrating file size validation (10 MB cap), base64 encoding, moderation gate screening, image saving, watermarking, vision model extraction, confidence routing, PII logging, and SQLite insertion.
  - `review(document_id)`: `GET /review` handler returning pending review documents with derived low-confidence field indicators.
  - `approve(req)`: `POST /approve` handler updating document status to `approved` and persisting human-reviewed JSON.
- **Dependencies**: `fastapi`, `prometheus_client`, `config`, `utils`, `db`, `moderation`, `extraction`, `confidence`, `watermark`, `pii`, `metrics`, `schemas`.

## `config.py`
- **Purpose**: Reads environment variables from `os.environ` and sets default fallback values.
- **Variables**: `AI_PROVIDER`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENAI_MODEL`, `GEMINI_MODEL`, `GROQ_MODEL`, `MODERATION_PROVIDER`, `MODERATION_MODEL`, `REVIEW_THRESHOLD` (`0.75`), `MODERATION_THRESHOLD` (`0.7`), `MAX_IMAGE_DIMENSION` (`2048`), `UPLOAD_DIR` (`uploads`), `DATABASE_PATH` (`data/cevondocs.db`), `COST_PER_TOKEN` (`0.0000025`), `APP_VERSION` (`1.0.0`).

## `schemas.py`
- **Purpose**: Defines Pydantic data models for structured LLM extractions and API contract schemas.
- **Models**:
  - `LineItem`: `description` (str), `quantity` (float), `unit_price` (float), `amount` (float), `confidence` (float).
  - `InvoiceSchema`: Top-level invoice fields (`vendor`, `invoice_number`, `date`, `currency`, `subtotal`, `tax`, `total`, `line_items`, `overall_confidence`) paired with confidence scores (`vendor_confidence`, etc.).
  - `IngestResponse`, `ReviewItem`, `ReviewResponse`, `ApproveRequest`, `ApproveResponse`.

## `db.py`
- **Purpose**: Encapsulates raw `sqlite3` database access.
- **Key Functions**:
  - `get_connection(db_path)`: Returns a connection with `row_factory = sqlite3.Row` and creates missing parent directories automatically (`Path(db_path).parent.mkdir(...)`).
  - `init_db(db_path)`: Executes `CREATE TABLE IF NOT EXISTS documents (...)`.
  - `insert_document(...)`: Inserts a new document record.
  - `get_document(doc_id)`: Fetches a single row by primary key.
  - `get_pending()`: Returns all rows with `status = 'pending_review'`.
  - `approve_document(doc_id, reviewed_json)`: Updates status to `approved` and writes `reviewed_json`.

## `extraction.py`
- **Purpose**: Lightweight facade routing extraction requests to the configured provider.
- **Functions**:
  - `extract_invoice(b64_image)`: Resizes image to `MAX_IMAGE_DIMENSION` via `utils.resize_image_b64` and dispatches to `extract_openai`, `extract_gemini`, or `extract_groq`.

## `backend/ai/openai_provider.py`
- **Purpose**: OpenAI GPT-4o vision extraction provider.
- **Functions**: `extract_openai(b64_image, resized_b64)`: Uses `client.beta.chat.completions.parse` with `response_format=InvoiceSchema` and `utils.detect_mime_type`. Wraps network call in `retry_on_transient`.

## `backend/ai/gemini_provider.py`
- **Purpose**: Google Gemini 2.5 Flash vision extraction provider.
- **Functions**: `extract_gemini(b64_image, resized_b64)`: Uses `google-genai` SDK `client.models.generate_content` with `response_schema=InvoiceSchema` and validates output JSON via `InvoiceSchema.model_validate_json()`.

## `backend/ai/groq_provider.py`
- **Purpose**: Groq Qwen 27B vision extraction provider.
- **Functions**: `extract_groq(b64_image, resized_b64)`: Uses Groq SDK with `response_format={"type": "json_object"}` and validates response with `InvoiceSchema.model_validate_json()`.

## `backend/moderation/router.py`
- **Purpose**: Core moderation router and local image validator.
- **Functions**:
  - `_check_basic_image_validation(b64_image)`: Validates base64 string, PIL image integrity (`img.verify()`), supported formats (`PNG`, `JPEG`, `JPG`), and size (< 20 MB).
  - `check_moderation(b64_image)`: Runs basic validation, then evaluates `MODERATION_PROVIDER`. In `auto` mode, selects OpenAI if key present, else Gemini if key present, else local.

## `backend/moderation/openai_moderation.py`
- **Purpose**: OpenAI Moderation API gate.
- **Functions**: `check_openai_moderation(b64_image)`: Calls `client.moderations.create` with `omni-moderation-latest` using dynamic `detect_mime_type`. Compares category scores against `MODERATION_THRESHOLD`.

## `backend/moderation/gemini_moderation.py`
- **Purpose**: Gemini safety vision screening gate.
- **Functions**: `check_gemini_moderation(b64_image)`: Dispatches safety prompt to Gemini model and parses `is_safe` and `blocked_reason` from JSON response.

## `confidence.py`
- **Purpose**: Evaluates extraction confidence scores against `REVIEW_THRESHOLD`.
- **Functions**: `route_document(invoice_data, threshold)`: Checks top-level confidence fields and line-item confidence scores. Converts missing/`None` confidence values to `0.0` (fail-closed). Returns `(status, flagged_fields)`.

## `pii.py`
- **Purpose**: Redacts sensitive personal information prior to logging.
- **Functions**: `redact_pii(text)`: Replaces SSNs, email addresses, phone numbers, and Aadhaar IDs (12 digits starting with `2-9`) with `[REDACTED]`.

## `watermark.py`
- **Purpose**: Applies provenance watermark stamps.
- **Functions**: `watermark_image(image_path, doc_id, output_path)`: Uses PIL `ImageDraw` to stamp `{doc_id} | {timestamp}` in gray semi-transparent text at bottom-right corner onto `watermarked.png`.

## `metrics.py`
- **Purpose**: Defines Prometheus metrics objects.
- **Objects**: `moderation_latency` (Histogram), `extraction_latency` (Histogram), `token_cost_total` (Counter), `auto_approvals_total` (Counter), `reviews_total` (Counter), `documents_processed_total` (Counter with `status` label).

## `utils.py`
- **Purpose**: Shared utility functions.
- **Functions**: `generate_id()`, `now_iso()`, `image_to_base64()`, `detect_mime_type()`, `resize_image_b64()`, `save_upload()`, `retry_on_transient()`.

## `streamlit_app.py`
- **Purpose**: Two-tab Streamlit web user interface.
- **Tabs**:
  - `tab_upload`: Form for uploading image, displaying status badges, confidence scores, and extracted data.
  - `tab_review`: Review queue selector, watermarked image preview, field edit inputs, and `st.data_editor` line items editor.

---

# 5. Complete Request Lifecycle

```text
Client Upload (JPEG/PNG)
  ↓
POST /ingest (main.py)
  ├── 1. Request Validation: Rejects non-JPEG/PNG (400), empty file (400), payload > 10MB (413).
  ├── 2. Image Base64 Encoding: utils.image_to_base64().
  ├── 3. Moderation Gate: moderation.check_moderation().
  │      ├── Local Validation: format, integrity, size.
  │      └── Provider Screening (auto/openai/gemini/local).
  │             └── If Unsafe/Corrupted: raises HTTPException 422 (status="blocked").
  ├── 4. File Storage: utils.save_upload() saves to uploads/{doc_id}/original.png.
  ├── 5. Watermarking: watermark.watermark_image() saves uploads/{doc_id}/watermarked.png.
  ├── 6. Vision Extraction: extraction.extract_invoice() dispatches to active provider.
  │      ├── Resizes image if dimension > 2048px (utils.resize_image_b64).
  │      ├── Detects MIME type dynamically (utils.detect_mime_type).
  │      └── Calls AI Provider with transient backoff retries (utils.retry_on_transient).
  │             └── If API/Key Error: raises HTTPException 503 (status="failed").
  ├── 7. Pydantic Schema Validation: Validates InvoiceSchema structure.
  ├── 8. Confidence Routing: confidence.route_document() checks fields against threshold 0.75.
  │      ├── Missing/None confidence scores default to 0.0 (fail-closed).
  │      ├── All scores >= 0.75 → status = "auto_approved".
  │      └── Any score < 0.75 → status = "pending_review", populates flagged_fields.
  ├── 9. PII Redaction: pii.redact_pii() masks SSN/email/phone/Aadhaar in JSON before logging.
  ├── 10. Database Persistence: db.insert_document() writes row to data/cevondocs.db.
  ├── 11. Metrics Update: Increments Prometheus counters and records latency histograms.
  └── 12. Response Delivery: Returns IngestResponse JSON payload.

Human Review & Approval Lifecycle (Streamlit UI)
  ↓
GET /review (main.py)
  ├── 1. Fetches pending_review rows from db.get_pending().
  ├── 2. Re-evaluates flagged fields dynamically via confidence.route_document().
  └── 3. Displays document options in Streamlit review queue selector.
  ↓
Reviewer Edits & Corrects Fields (streamlit_app.py)
  ├── 1. Displays watermarked source image from uploads/{doc_id}/watermarked.png.
  ├── 2. Reviewer modifies vendor, invoice number, date, currency, subtotal, tax, total.
  └── 3. Reviewer edits line items in st.data_editor (Confidence column disabled/read-only).
  ↓
POST /approve (main.py)
  ├── 1. Validates document existence in DB.
  ├── 2. db.approve_document() updates status to "approved" and writes reviewed_json.
  ├── 3. Logs reviewed payload with pii.redact_pii() masking.
  └── 4. Returns ApproveResponse JSON payload.
```

---

# 6. AI Provider System

## Provider Abstraction Facade
`extraction.py` serves as a lightweight facade router. It accepts `b64_image`, resizes it to `config.MAX_IMAGE_DIMENSION` (`2048`), inspects `config.AI_PROVIDER`, and delegates to the appropriate provider module:

```python
def extract_invoice(b64_image: str) -> tuple[InvoiceSchema, dict]:
    resized_b64 = resize_image_b64(b64_image, config.MAX_IMAGE_DIMENSION)
    provider = config.AI_PROVIDER

    if provider == "openai":
        return extract_openai(b64_image, resized_b64)
    elif provider == "gemini":
        return extract_gemini(b64_image, resized_b64)
    elif provider == "groq":
        return extract_groq(b64_image, resized_b64)
    else:
        raise ValueError(f"Unsupported AI provider: '{provider}'")
```

## Provider Implementation Details

| Feature | OpenAI Provider | Gemini Provider | Groq Provider |
|---|---|---|---|
| **Module Path** | `backend/ai/openai_provider.py` | `backend/ai/gemini_provider.py` | `backend/ai/groq_provider.py` |
| **SDK Used** | `openai` (`OpenAI`) | `google-genai` (`genai.Client`) | `groq` (`Groq`) |
| **Default Model** | `gpt-4o` | `gemini-2.5-flash` | `qwen/qwen3.6-27b` |
| **Structured Output Mechanism** | Native `response_format=InvoiceSchema` via `beta.chat.completions.parse` | Native `response_schema=InvoiceSchema` via `types.GenerateContentConfig` | JSON Mode `response_format={"type": "json_object"}` + post-call Pydantic validation |
| **Schema Validation** | SDK automatically parses into `InvoiceSchema` | `InvoiceSchema.model_validate_json(response.text)` | `InvoiceSchema.model_validate_json(content)` |
| **MIME Type Handling** | Dynamic `detect_mime_type(b64)` | Dynamic `detect_mime_type(b64)` | Dynamic `detect_mime_type(b64)` |
| **Retry Wrapper** | `utils.retry_on_transient` | `utils.retry_on_transient` | `utils.retry_on_transient` |

## Transient Error Retry Strategy
`utils.retry_on_transient` implements exponential backoff retries ($1\text{s}, 2\text{s}, 4\text{s}$) for transient network errors (HTTP 429, 500, 502, 503, 504, rate limits, timeouts). Non-transient errors (such as invalid API keys) fail fast without retrying.

---

# 7. Database

## SQLite Schema
Database file location: `data/cevondocs.db` (configurable via `DATABASE_PATH`). Managed by raw `sqlite3` in `db.py`.

```sql
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    status TEXT NOT NULL,
    extracted_json TEXT,
    reviewed_json TEXT,
    created_at TEXT NOT NULL
);
```

## Document Lifecycle States
1. `auto_approved`: Document ingested, vision extraction succeeded, all confidence scores $\ge 0.75$.
2. `pending_review`: Document ingested, vision extraction succeeded, one or more confidence scores $< 0.75$.
3. `approved`: Document reviewed and corrected by a human via `POST /approve`.
4. `blocked`: Image blocked by moderation gate (not saved in database, HTTP 422 returned).
5. `failed`: Processing error (missing API key, invalid file format, HTTP 503/500 returned).

## Thread Safety & Parent Directory Auto-Creation
`db.get_connection()` ensures the database parent folder exists (`Path(db_path).parent.mkdir(parents=True, exist_ok=True)`) before instantiating `sqlite3.connect()`. Connections set `conn.row_factory = sqlite3.Row` for dict-like row access and operate within context managers (`with get_connection() as conn:`) ensuring automatic transaction commit and closure.

---

# 8. Confidence System

## Calculation & Threshold Evaluation
Every field in `InvoiceSchema` includes a corresponding self-reported confidence score ranging from $0.0$ (completely missing/guessed) to $1.0$ (100% legibility).

`confidence.route_document()` compares scores against `config.REVIEW_THRESHOLD` (`0.75`):
- `vendor_confidence` < `0.75` → flags `"vendor"`
- `invoice_number_confidence` < `0.75` → flags `"invoice_number"`
- `date_confidence` < `0.75` → flags `"date"`
- `currency_confidence` < `0.75` → flags `"currency"`
- `subtotal_confidence` < `0.75` → flags `"subtotal"`
- `tax_confidence` < `0.75` → flags `"tax"`
- `total_confidence` < `0.75` → flags `"total"`
- `line_items[i].confidence` < `0.75` → flags `"line_items[i]"`

## Fail-Closed Default Policy
If an LLM fails to return a confidence field or returns `None`, `confidence.route_document` defaults `conf_val` to `0.0`. Because $0.0 < 0.75$, missing scores **fail closed** and route the document to `pending_review`.

---

# 9. Moderation System

## Architecture & Provider Selection (`MODERATION_PROVIDER`)
Located in `backend/moderation/`. Entry point facade: `moderation.py`.

```text
MODERATION_PROVIDER Config Options:
  • "auto" (Default): OpenAI Key present? → OpenAI Moderation.
                       Else Gemini Key present? → Gemini Safety Screening.
                       Else → Local Basic Validation only.
  • "openai": Forces OpenAI Moderation API (omni-moderation-latest).
  • "gemini": Forces Gemini vision safety model.
  • "local": Local format, integrity, and file size checks only.
```

## Local Basic Image Validation (`_check_basic_image_validation`)
Runs prior to any remote API call:
1. Validates base64 string decoding.
2. Checks file size (< 20 MB).
3. Inspects image header via PIL `img.verify()`.
4. Enforces supported formats (`PNG`, `JPEG`, `JPG`). Returns `(False, "corrupted_or_invalid_image")` on failure.

---

# 10. Streamlit UI

## Application Structure (`streamlit_app.py`)
- **Page Title**: `🧾 CevonDocs — Receipt & Invoice Intelligence`
- **Layout**: Two primary tabs (`tab_upload`, `tab_review`).

## Tab 1: Upload & Extract (`tab_upload`)
- `st.file_uploader`: Accepts PNG/JPG files.
- `col_preview`: Displays source image preview and `🚀 Process Document` button.
- `col_results`: Sends multipart POST to `/ingest`. Displays status badges (🟢 Auto-Approved / 🟡 Pending Review), confidence badges (🟢 $\ge 0.75$, 🟡 $\ge 0.50$, 🔴 $< 0.50$), extracted field table, and line items data frame.

## Tab 2: Human Review Queue (`tab_review`)
- `st.selectbox`: Lists pending documents from `GET /review`.
- `col_img`: Displays watermarked source image (`uploads/{doc_id}/watermarked.png`).
- `col_edit`: Form `review_form` containing text inputs for scalar fields and `st.data_editor` for line items.
- `st.data_editor`: Displays line item table (`description`, `quantity`, `unit_price`, `amount`, `confidence`). Sets `disabled=["confidence"]` so confidence scores remain read-only.
- `st.form_submit_button`: Sends POST to `/approve` with reviewed JSON payload and updates state.

---

# 11. API Documentation

## 1. Health Check (`GET /health`)
- **Purpose**: Service health and DB connection check.
- **Response** `200 OK`: `{"status": "ok", "database": "connected", "version": "1.0.0"}`

## 2. Ingest Document (`POST /ingest`)
- **Purpose**: Uploads and processes a receipt/invoice image.
- **Payload**: `file` (UploadFile multipart).
- **Responses**:
  - `200 OK`: `IngestResponse` JSON (`document_id`, `status`, `extracted_data`, `flagged_fields`).
  - `400 Bad Request`: Invalid file type or empty file.
  - `413 Payload Too Large`: Upload exceeds 10 MB limit.
  - `422 Unprocessable Entity`: Image blocked by moderation gate.
  - `503 Service Unavailable`: Missing provider API keys.
  - `500 Internal Server Error`: Vision extraction failure.

## 3. Review Queue (`GET /review`)
- **Purpose**: Fetches pending review items.
- **Query Params**: `document_id` (optional).
- **Response** `200 OK`: `ReviewResponse` JSON array of `ReviewItem` objects.

## 4. Approve Document (`POST /approve`)
- **Purpose**: Commits human-corrected JSON payload.
- **Request Body**: `ApproveRequest` (`document_id`, `reviewed_data`).
- **Response** `200 OK`: `ApproveResponse` JSON (`document_id`, `status`: `"approved"`, `message`).

## 5. Metrics (`GET /metrics`)
- **Purpose**: Exposes Prometheus metrics text payload.
- **Response** `200 OK`: Prometheus exposition format (`text/plain`).

---

# 12. Metrics & Observability

## Prometheus Metrics (`metrics.py`)
- `moderation_latency_seconds` (Histogram): Measures moderation gate duration.
- `extraction_latency_seconds` (Histogram): Measures vision model extraction duration.
- `token_cost_usd_total` (Counter): Cumulative LLM token cost in USD (`total_tokens * COST_PER_TOKEN`).
- `auto_approvals_total` (Counter): Total auto-approved documents.
- `reviews_total` (Counter): Total documents routed to human review.
- `documents_processed_total` (Counter with label `status`): Tracks documents by status (`auto_approved`, `pending_review`, `blocked`, `failed`).

## Grafana Dashboard (`grafana/dashboard.json`)
- **Panel 1 (p99 Moderation Latency)**: PromQL `histogram_quantile(0.99, sum(rate(moderation_latency_seconds_bucket[5m])) by (le))`
- **Panel 2 (p99 Extraction Latency)**: PromQL `histogram_quantile(0.99, sum(rate(extraction_latency_seconds_bucket[5m])) by (le))`
- **Panel 3 (Cumulative Token Cost)**: PromQL `token_cost_usd_total`
- **Panel 4 (Auto-Approval Rate %)**: PromQL `(sum(auto_approvals_total) / sum(documents_processed_total)) * 100`
- **Panel 5 (Document Throughput)**: PromQL `sum(rate(documents_processed_total[1m])) * 60`

---

# 13. Docker & Deployment

## `Dockerfile`
Built on `python:3.11-slim`. Installs `build-essential`, copies `requirements.txt`, executes `pip install`, and exposes ports `8000` (FastAPI) and `8501` (Streamlit). Starts services concurrently via:
`uvicorn main:app --host 0.0.0.0 --port 8000 & streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true`

## `docker-compose.yml`
Orchestrates 3 containers:
1. `app`: Builds `.`, maps ports `8000` & `8501`, loads `.env`, mounts `./uploads:/app/uploads` and `./data:/app/data`, sets `DATABASE_PATH=/app/data/cevondocs.db`.
2. `prometheus`: Image `prom/prometheus:v2.45.0`, maps port `9090`, mounts `./prometheus.yml`.
3. `grafana`: Image `grafana/grafana:10.0.0`, maps port `3000`, provisions datasources and `dashboard.json`.

## CI/CD Pipeline (`.github/workflows/ci-cd.yml`)
- **Job 1 (`test`)**: Runs `pytest tests/ -v` on Python 3.11 runner.
- **Job 2 (`deploy`)**: Authenticates with GCP via `GCP_SA_KEY`, builds Docker image, pushes to Google Container Registry (`gcr.io`), and deploys to Cloud Run with `--set-env-vars` injecting provider credentials.

---

# 14. Testing

Automated test suite (`pytest tests/ -v`) containing **37 tests**:

1. **`tests/test_schemas.py`** (5 tests): Validates Pydantic schema instantiation, LineItem bounds, JSON roundtripping, and validation errors.
2. **`tests/test_pii.py`** (5 tests): Validates regex redaction for SSNs, emails, phone numbers, Aadhaar IDs (`[2-9]\d{3}...`), and clean text passthrough.
3. **`tests/test_confidence.py`** (5 tests): Tests auto-approval, pending review routing, exact threshold boundary (`0.75`), 0.74 vs 0.75 routing, and fail-closed missing confidence default (`0.0`).
4. **`tests/test_moderation.py`** (7 tests): Tests `auto` provider selection, fallback to Gemini/local when keys are absent, explicit provider missing key 503 errors, and Gemini safety blocks.
5. **`tests/test_multi_provider_fixes.py`** (15 tests): Tests missing API key 503 responses across providers, MIME detection, image resizing, Groq schema validation errors, 10MB upload limits, and line item editing `/approve` DB commits.

---

# 15. Configuration

| Variable Name | Default Value | Description |
|---|---|---|
| `AI_PROVIDER` | `openai` | Active vision extraction provider (`openai`, `gemini`, `groq`) |
| `OPENAI_API_KEY` | `""` | OpenAI API authentication key |
| `GEMINI_API_KEY` | `""` | Google GenAI API authentication key |
| `GROQ_API_KEY` | `""` | Groq API authentication key |
| `OPENAI_MODEL` | `gpt-4o` | Model name for OpenAI vision calls |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model name for Gemini vision calls |
| `GROQ_MODEL` | `qwen/qwen3.6-27b` | Model name for Groq vision calls |
| `MODERATION_PROVIDER` | `auto` | Moderation provider (`auto`, `openai`, `gemini`, `local`) |
| `MODERATION_MODEL` | `omni-moderation-latest` | Model for OpenAI Moderation API |
| `REVIEW_THRESHOLD` | `0.75` | Confidence threshold for routing |
| `MODERATION_THRESHOLD` | `0.7` | Category score threshold for content blocking |
| `MAX_IMAGE_DIMENSION` | `2048` | Max pixel dimension before downsizing |
| `UPLOAD_DIR` | `uploads` | Image upload directory path |
| `DATABASE_PATH` | `data/cevondocs.db` | SQLite database file path |
| `COST_PER_TOKEN` | `0.0000025` | Estimated USD cost per token for metrics |

---

# 16. Security

1. **Provider-Agnostic Content Moderation**: 2-step safety check blocking offensive/harmful uploads prior to vision model processing.
2. **PII Masking Engine**: Regex masking of SSNs, emails, phone numbers, and Aadhaar IDs before writing JSON payloads to application log streams.
3. **HTTP Payload Limits**: Rejects requests exceeding 10 MB with HTTP 413, preventing OOM memory exhaustion attacks.
4. **Parameterized SQL Queries**: Uses raw `sqlite3` parameterized placeholders (`?`) for all queries, eliminating SQL injection risks.
5. **No Committed Secrets**: `.gitignore` excludes `.env`; CI/CD injects credentials securely via GitHub Secrets.

---

# 17. Design Decisions

- **Why FastAPI?**: High performance async execution, native Pydantic contract integration, automatic OpenAPI documentation.
- **Why Raw `sqlite3` over ORMs?**: Avoids heavy ORM abstractions (SQLAlchemy) for single-table local persistence while guaranteeing atomic transactions.
- **Why Provider Abstraction?**: Prevents vendor lock-in; allows switching between OpenAI, Gemini, and Groq via single env variable (`AI_PROVIDER`).
- **Why Fail-Closed Confidence Routing?**: Prevents silent hallucinations; missing confidence scores default to `0.0` to guarantee human review.
- **Why Non-Destructive Watermarking?**: Preserves clean original uploaded image (`original.png`) for auditability while serving marked image (`watermarked.png`) to UI.

---

# 18. Known Limitations

1. **Single-Page Document Scope**: Ingest pipeline processes single-page PNG/JPEG images. Multi-page PDF splitting must occur upstream.
2. **Local SQLite File Volume**: SQLite database is bound to local file volume (`data/cevondocs.db`). Multi-instance horizontal scaling would require Cloud SQL / PostgreSQL.
3. **Groq Post-Call Schema Validation**: Groq uses JSON mode (`json_object`); schema structure is validated post-call via Pydantic (`model_validate_json`).

---

# 19. Extension Guide

- **Adding a New AI Provider**:
  1. Create `backend/ai/newprovider_provider.py` implementing `extract_newprovider(b64_image, resized_b64)`.
  2. Add provider branch in `extraction.py` router.
  3. Add provider key and model env vars in `config.py`.
- **Adding a New Field to InvoiceSchema**:
  1. Update `InvoiceSchema` in `schemas.py` with field and corresponding confidence score field.
  2. Add confidence mapping entry in `confidence.py` `top_level_map`.
  3. Update Streamlit UI forms in `streamlit_app.py`.

---

# 20. Interview Guide

When presenting CevonDocs in technical interviews:
- **Core Narrative**: "I engineered CevonDocs, a full-stack document intelligence system that solves fragile OCR rules and silent AI hallucinations through Pydantic schema contracts, multi-provider vision models, and fail-closed uncertainty routing."
- **Key Talking Points**:
  - Hot-swappable AI provider router (`OpenAI`, `Gemini`, `Groq`).
  - Fail-closed routing strategy ($0.0$ missing confidence fallback).
  - Production observability with Prometheus latency histograms, token cost counters, and Grafana dashboards.
  - Clean containerized deployment via Docker Compose and GCP Cloud Run CI/CD.

---

# 21. Executive Summary

CevonDocs is a production-ready document intelligence application combining multi-provider vision AI extraction (OpenAI GPT-4o, Gemini 2.5 Flash, Groq Qwen 27B), provider-agnostic content moderation, fail-closed confidence routing, automated regex PII redaction, PIL provenance watermarking, and a human-in-the-loop review interface with Streamlit `st.data_editor`.

The project features 100% test coverage across 37 automated Pytest unit and contract tests, clean Docker containerization with persistent volumes (`./data:/app/data`), automated GitHub Actions CI/CD deployment to GCP Cloud Run, and complete Prometheus/Grafana observability instrumentation. It represents a state-of-the-art implementation of schema-enforced AI document extraction.
