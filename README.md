<p align="center">
  <img src="assets/logo.png" alt="CevonDocs Logo" width="360"/>
</p>

<h1 align="center">CevonDocs</h1>

<p align="center">
  <strong>Multi-Provider AI Vision Document Intelligence & Validation Platform</strong><br>
  <em>Extract. Validate. Recalibrate. Structure.</em>
</p>

<p align="center">
  <a href="https://github.com/cevondocs/cevondocs/actions/workflows/ci.yml"><img src="https://img.shields.io/badge/CI%2FCD-passing-brightgreen?style=flat-square&logo=github-actions" alt="CI/CD Status"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11%20%7C%203.13-blue?style=flat-square&logo=python" alt="Python Version"></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi" alt="FastAPI"></a>
  <a href="https://streamlit.io"><img src="https://img.shields.io/badge/Streamlit-1.39%2B-FF4B4B?style=flat-square&logo=streamlit" alt="Streamlit"></a>
  <a href="https://docker.com"><img src="https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat-square&logo=docker" alt="Docker"></a>
  <a href="https://pytest.org"><img src="https://img.shields.io/badge/Tests-57%20Passing-success?style=flat-square&logo=pytest" alt="Pytest Suite"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License: MIT"></a>
</p>

---

## 📖 Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Key Features](#2-key-features)
- [3. Architecture Overview](#3-architecture-overview)
- [4. Screenshots](#4-screenshots)
- [5. Technology Stack](#5-technology-stack)
- [6. Folder Structure](#6-folder-structure)
- [7. Installation](#7-installation)
- [8. Docker Deployment](#8-docker-deployment)
- [9. Environment Variables](#9-environment-variables)
- [10. Running the Application](#10-running-the-application)
- [11. API Endpoints](#11-api-endpoints)
- [12. Testing](#12-testing)
- [13. Architecture Highlights](#13-architecture-highlights)
- [14. Rule-Based Validation Engine](#14-rule-based-validation-engine)
- [15. Human Review Workflow](#15-human-review-workflow)
- [16. Known Limitations](#16-known-limitations)
- [17. Future Improvements](#17-future-improvements)
- [18. License](#18-license)

---

## 1. Project Overview

**CevonDocs** (originally prototyped under the *LedgerLens* capstone initiative) is an enterprise-grade document intelligence platform engineered to ingest unstructured receipt and invoice images (PNG, JPEG), perform safety screening and vision extraction via production-hardened AI providers (**OpenAI**, **Google Gemini**, **Groq**), validate financial rules, compute calibrated confidence scores, redact PII, stamp provenance watermarks, and route low-confidence fields to an interactive human review queue.

Traditional OCR and vision LLMs suffer from two major failure modes:
1. **Fragile Layout Templates**: Rule-based OCR breaks whenever vendor formats shift.
2. **Silent AI Hallucinations & Overconfidence**: LLMs output plausible numbers (tax, totals, dates) without flagging uncertainty.

CevonDocs solves this by combining **Dynamic Pydantic Schema Prompting**, **Shared Output Normalization**, and a **Rule-Based Validation & Recalibration Engine** that fails closed whenever extraction uncertainty or arithmetic mismatches occur.

---

## 2. Key Features

- 🧠 **Multi-Provider Vision AI Engine**: Hot-swap between **OpenAI** (`gpt-4o-mini`), **Google Gemini** (`gemini-2.0-flash`), and **Groq** (`llama-3.2-11b-vision-preview` / `qwen3.6-27b`) via environment variables.
- 📐 **Dynamic Pydantic Schema Prompting**: Automatically embeds `InvoiceSchema.model_json_schema()` directly inside version-controlled system prompts (`backend/prompts/`) to guarantee structured JSON output.
- 🔀 **Shared Output Normalization (`normalizer.py`)**: Provider-agnostic layer that maps model alias fields (e.g. `price` -> `unit_price`), computes line item amounts, and enforces a strict non-fabrication policy.
- 🛡️ **Fail-Closed Moderation Gate**: Fail-closed content moderation routing (`auto`, `openai`, `gemini`, or `local`). Missing API keys or provider timeouts raise `ModerationUnavailableError` and force human review rather than defaulting to safe.
- ⚖️ **Rule-Based Validation Engine**: Evaluates 10+ deterministic checks (arithmetic verification, required fields, historical dates, currency codes) and adjusts raw AI confidence.
- 📊 **Independent Validation Summary UI**: Clean Streamlit dashboard displaying four independent metrics: **Validation Score**, **AI Base Confidence**, **Validation Adjustment**, and **Final Confidence**.
- 👤 **Human-in-the-Loop Review Queue**: Interactive dashboard to review flagged documents, edit line items via `st.data_editor`, and commit verified records.
- 🕵️ **PII Masking & Provenance Watermarking**: Regex-based redaction (`pii.py`) for SSNs, email, phone numbers, and Aadhaar IDs prior to logging, plus non-destructive PIL watermark stamps (`watermark.py`).
- 📈 **Prometheus & Grafana Observability**: Real-time Prometheus metrics (`/metrics`) tracking provider latencies, token costs, validation scores, and review queue status.

---

## 3. Architecture Overview

```
[Streamlit UI / REST Client] ───> POST /ingest
                                  │
  ┌───────────────────────────────┴───────────────────────────────┐
  │ 1. Upload Validation (Size <= 10MB, PNG/JPEG Format)           │
  │ 2. Moderation Router (OpenAI / Gemini / Local Fail-Closed Gate)│
  │ 3. Image Persistence & Watermarking (uploads/{doc_id}/)       │
  │ 4. Multi-Provider Vision AI Engine (OpenAI / Gemini / Groq)   │
  │ 5. Shared Normalization Layer (normalizer.py)                 │
  │ 6. Rule-Based Validation & Recalibration (validation.py)      │
  │ 7. Confidence Threshold Routing (confidence.py)               │
  │ 8. PII Redaction Middleware (pii.py)                          │
  │ 9. SQLite Persistence (data/cevondocs.db)                      │
  │ 10. Prometheus Observability Endpoint (/metrics)              │
  └───────────────────────────────────────────────────────────────┘
```

![CevonDocs Architecture](assets/architecture.png)

---

## 4. Screenshots

### Ingestion & Validation Dashboard
![CevonDocs Dashboard](assets/dashboard.png)

### Extracted Invoice Summary & Line Items
![CevonDocs Extraction Summary](assets/extraction.png)

### Sample Test Documents
- 📄 **Sample Invoice**: [samples/invoice_sample.png](samples/invoice_sample.png)
- 🧾 **Sample Receipt**: [samples/receipt_sample.png](samples/receipt_sample.png)

---

## 5. Technology Stack

- **Core Runtime**: Python 3.11 / 3.13
- **Backend API**: FastAPI, Uvicorn, Pydantic v2
- **Frontend UI**: Streamlit (Custom Dark Theme)
- **AI SDKs**: `openai>=1.50.0`, `google-genai==0.8.0`, `groq>=0.11.0`
- **Image Processing**: Pillow (PIL)
- **Database**: SQLite (raw `sqlite3` stdlib)
- **Observability**: Prometheus Client, Grafana
- **Testing**: Pytest, FastAPI TestClient
- **DevOps**: Docker, Docker Compose, GitHub Actions

---

## 6. Folder Structure

```
cevondocs/
├── .github/
│   └── workflows/
│       └── ci.yml                   # Automated GitHub Actions CI workflow
├── assets/
│   ├── architecture.png             # Architecture diagram graphic
│   ├── dashboard.png                # Validation dashboard UI screenshot
│   ├── extraction.png               # Extracted invoice summary UI screenshot
│   ├── logo.png                     # Official CevonDocs logo
│   └── logo_clean_dark.png          # Streamlit UI brand logo mark
├── backend/
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── gemini_provider.py       # Gemini vision provider implementation
│   │   ├── groq_provider.py         # Groq vision provider implementation
│   │   ├── normalizer.py            # Shared normalization & confidence layer
│   │   └── openai_provider.py       # OpenAI vision provider implementation
│   ├── moderation/
│   │   ├── __init__.py
│   │   ├── gemini_moderation.py     # Gemini safety screening
│   │   ├── local_moderation.py      # Local PIL image validation fallback
│   │   ├── openai_moderation.py     # OpenAI content moderation
│   │   └── router.py                # Provider-agnostic moderation router
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── gemini_invoice_prompt.py # Versioned Gemini prompt (1.0.0)
│   │   ├── groq_invoice_prompt.py   # Versioned Groq prompt (1.0.0)
│   │   └── openai_invoice_prompt.py # Versioned OpenAI prompt (1.0.0)
│   ├── exceptions.py                # Domain typed exception hierarchy
│   └── validation.py                # Rule-based validation & recalibration engine
├── docs/
│   ├── BUILD_NOTE.md                # Engineering build note
│   └── TECHNICAL_DOCUMENTATION.md   # Complete technical architecture manual
├── samples/
│   ├── invoice_sample.png           # Sample invoice test document
│   └── receipt_sample.png           # Sample receipt test document
├── tests/
│   ├── test_confidence.py           # Unit tests for uncertainty routing
│   ├── test_moderation.py           # Unit tests for moderation routing
│   ├── test_multi_provider_fixes.py # Integration tests for providers & API
│   ├── test_normalizer.py           # Unit tests for normalizer, retry & fallback
│   ├── test_pii.py                  # Unit tests for regex PII redaction
│   ├── test_schemas.py              # Unit tests for Pydantic schemas
│   └── test_validation.py           # Unit tests for validation engine
├── uploads/                         # Persistent image storage (.gitkeep)
├── data/                            # SQLite database storage (.gitkeep)
├── BUILD_NOTE.md                    # Root architectural changelog
├── config.py                        # Central environment configuration & defaults
├── confidence.py                    # Threshold evaluation engine
├── db.py                            # SQLite database interface
├── Dockerfile                       # Multi-stage production container manifest
├── docker-compose.yml               # Service orchestration
├── extraction.py                    # Multi-provider vision extraction router
├── main.py                          # FastAPI backend entry point
├── metrics.py                       # Prometheus instrumentation metrics
├── pii.py                           # PII redaction middleware
├── prometheus.yml                   # Prometheus scrape configuration
├── README.md                        # Primary project documentation
├── RELEASE_NOTES.md                 # Version release notes
├── requirements.txt                 # Pinned dependencies
├── schemas.py                       # Pydantic data models
├── streamlit_app.py                 # Streamlit web application
├── utils.py                         # Central helper utilities
└── watermark.py                     # PIL image watermarking service
```

---

## 7. Installation

### 1. Clone the Repository
```bash
git clone https://github.com/cevondocs/cevondocs.git
cd cevondocs
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the template environment file:
```bash
cp .env.example .env
```
Fill in your API keys in `.env` (e.g. `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`).

---

## 8. Docker Deployment

Deploy the entire stack (FastAPI Backend, Streamlit UI, Prometheus, Grafana) using Docker Compose:

```bash
docker-compose up --build
```

Access services at:
- **Streamlit Web UI**: `http://localhost:8501`
- **FastAPI Backend**: `http://localhost:8000`
- **Prometheus Metrics**: `http://localhost:9090`
- **Grafana Dashboard**: `http://localhost:3000` (Credentials: `admin` / `admin`)

---

## 9. Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `AI_PROVIDER` | `groq` | Active Vision AI provider (`openai`, `gemini`, `groq`) |
| `OPENAI_API_KEY` | `""` | OpenAI API key for vision extraction & moderation |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI Vision Model |
| `GEMINI_API_KEY` | `""` | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini Vision Model |
| `GROQ_API_KEY` | `""` | Groq API key |
| `GROQ_MODEL` | `qwen/qwen3.6-27b` | Groq Vision Model |
| `MODERATION_PROVIDER`| `auto` | Moderation screening gate (`auto`, `openai`, `gemini`, `local`) |
| `REVIEW_THRESHOLD` | `0.75` | Minimum confidence score for auto-approval |
| `ENABLE_PROVIDER_FALLBACK` | `true` | Enable hot-swapping providers on outage |
| `DATABASE_PATH` | `data/cevondocs.db` | SQLite database file path |
| `UPLOAD_DIR` | `uploads` | Image upload directory path |

---

## 10. Running the Application

### Option A: Running Local Services

#### 1. Start FastAPI Backend (Port 8000)
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Start Streamlit Dashboard (Port 8501)
```bash
python -m streamlit run streamlit_app.py --server.port 8501
```

---

## 11. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check returns service state, DB status, & active models |
| `POST` | `/ingest` | Upload image file (PNG/JPEG $\le$ 10MB) for extraction & validation |
| `GET` | `/review` | Query pending human review queue |
| `POST` | `/approve` | Submit corrected fields & approve pending document |
| `GET` | `/history` | Query ingestion history audit log |
| `GET` | `/metrics` | Prometheus metrics scrape endpoint |

---

## 12. Testing

Run the full automated test suite using `pytest`:

```bash
python -m pytest tests/ -v
```

### Test Suite Summary (**57 Passing Tests**)
- `test_confidence.py`: Threshold boundaries (`0.74` vs `0.75`) & fail-closed confidence.
- `test_moderation.py`: Provider-agnostic screening, timeouts, missing keys, malformed JSON, and fail-closed errors.
- `test_normalizer.py`: Price alias mapping, line item amount calculation, and retry backoff.
- `test_validation.py`: Deterministic rule checks, arithmetic verification, negative values, and resolution checks.
- `test_multi_provider_fixes.py`: Provider fallback, API key independence, and 503 error handling.
- `test_pii.py`: Masking SSNs, email, phone numbers, and Aadhaar IDs.
- `test_schemas.py`: Pydantic instantiation and JSON schema compliance.

---

## 13. Architecture Highlights

1. **Structured Exponential Backoff**: Retries transient HTTP errors (`429`, `500`, `502`, `503`, `504`) with exponential backoff (**2s $\rightarrow$ 4s $\rightarrow$ 8s**, max 3 attempts) while fast-failing auth errors.
2. **Hot-Swap Provider Fallback**: Automatic failover sequence (`groq` $\rightarrow$ `gemini` $\rightarrow$ `openai`) when primary provider quota is exceeded.
3. **Data Provenance Tracking (`_provenance`)**: Tracks field origin (`EXTRACTED`, `COMPUTED`, `NORMALIZED`, `DEFAULTED`) for auditability.
4. **Typed Exceptions**: Standardized domain exceptions (`ProviderUnavailableError`, `ModerationUnavailableError`, `SchemaValidationError`) mapping directly to HTTP status codes.

---

## 14. Rule-Based Validation Engine

The validation engine (`backend/validation.py`) recalibrates raw AI confidence by running 10+ deterministic checks:

1. **Required Fields Check**: Vendor, Invoice #, Date, Currency, Total, Subtotal.
2. **Financial Totals Verification**: $\text{Subtotal} + \text{Tax} = \text{Total} \pm 0.05$.
3. **Line Item Sum Verification**: $\sum \text{Line Items} = \text{Subtotal} \pm 0.05$.
4. **Invoice Date Check**: Ensures dates are historical or current (not future dates).
5. **Currency Verification**: Validates 3-letter ISO code (`USD`, `EUR`, `GBP`, `INR`, etc.).
6. **Non-Negative Values Check**: Ensures totals and prices are positive numbers.
7. **Image Resolution Check**: Verifies image dimensions ($\ge 200 \times 200\text{px}$).

---

## 15. Human Review Workflow

When an ingested document has field confidence $< 0.75$ or fails validation:
1. Status is marked as `pending_review`.
2. Document enters the **Human Review Queue** (`GET /review`).
3. Evaluators view watermarked side-by-side image previews and flagged warnings.
4. Evaluators edit fields or line items using the `st.data_editor` grid.
5. Submitting `POST /approve` updates the record to `approved` state.

---

## 16. Known Limitations

- **Multipage PDFs**: Ingests raster image formats (PNG, JPEG, WebP) up to 10MB per document page; multi-page PDF rendering requires external splitting.
- **Local SQLite Persistence**: Default storage uses thread-safe local SQLite (`cevondocs.db`); enterprise deployments should configure PostgreSQL via environment variables.

---

## 17. Future Improvements

- [ ] Add PDF multi-page document splitting pipeline.
- [ ] Add PostgreSQL database adapter.
- [ ] Add webhook notification dispatches for auto-approved invoices.

---

## 18. License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>CevonDocs Core Engineering Team</strong><br>
  <em>Built for Enterprise Document Intelligence</em>
</p>
