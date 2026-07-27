# 🚀 CevonDocs v1.0.0 — Official GitHub Release Notes

We are thrilled to announce the official **v1.0.0 release of CevonDocs**, an enterprise-grade, multi-provider AI vision document intelligence and validation platform for extracting structured data from receipts and invoices!

---

## 🌟 What's New in v1.0.0

### 🧠 Multi-Provider AI Vision Engine
- Seamless support for **OpenAI** (`gpt-4o-mini`), **Google Gemini** (`gemini-2.0-flash`), and **Groq** (`llama-3.2-11b-vision-preview` / `qwen3.6-27b`).
- Dynamic Pydantic schema prompting embedding `InvoiceSchema.model_json_schema()` directly into prompts.
- Shared normalization layer (`normalizer.py`) mapping alias fields (`price` → `unit_price`), enforcing non-fabrication policies, and tracking source data provenance (`_provenance`).

### 🛡️ Fail-Closed Moderation & Rule Validation
- Fail-closed moderation gate raising `ModerationUnavailableError` on API timeouts or unconfigured credentials, forcing manual review rather than defaulting to safe.
- Deterministic rule-based validation engine (`validation.py`) evaluating 10+ financial arithmetic, currency ISO code, historical date, and required field checks.
- Refined Streamlit Validation Summary presenting four independent metrics: **Validation Score**, **AI Base Confidence**, **Validation Adjustment**, and **Final Confidence**.

### 👤 Human-in-the-Loop Review & Observability
- Interactive Streamlit review dashboard featuring side-by-side watermarked document previews, warning alerts, and an editable line item grid (`st.data_editor`).
- PII redaction middleware masking SSNs, emails, phone numbers, and Aadhaar IDs prior to logging.
- Prometheus metrics endpoint (`/metrics`) and pre-configured Grafana dashboards.
- Multi-stage production [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml), and GitHub Actions CI workflow ([ci.yml](.github/workflows/ci.yml)).
- Fully covered by **57 automated unit and integration tests**.

---

## 📄 Release Summary & Metadata

### Suggested GitHub Repository Description
```
AI-powered document intelligence platform for invoice and receipt extraction using multi-provider vision models, rule-based validation, confidence scoring, and human-in-the-loop review.
```

### Suggested GitHub Topics
`python` `fastapi` `streamlit` `document-ai` `invoice` `receipt` `ocr` `openai` `gemini` `groq` `docker` `prometheus` `grafana` `computer-vision` `ai`

---

## ⚠️ Known Limitations
- **Handwritten Invoices**: Cursive handwriting may reduce extraction confidence.
- **Low-Resolution Images**: Images $< 200 \times 200\text{px}$ trigger validation warnings.
- **Storage**: Default database is thread-safe local SQLite (`cevondocs.db`).
- **Ingestion**: Ingests single images per API call (no batch uploads).
- **Moderation**: Automated AI moderation requires OpenAI or Gemini API keys; falls back to `LOCAL_ONLY` basic image validation mode when unconfigured.

---

## 👥 Contributors & Feedback
Thank you to the engineering team and capstone evaluators! Feedback and contributions welcome.
