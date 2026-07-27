import json
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

import config
import utils
import db
import moderation
import extraction
import confidence
import watermark
import pii
import metrics
from schemas import (
    IngestResponse,
    ReviewResponse,
    ReviewItem,
    ApproveRequest,
    ApproveResponse,
)

from fastapi.responses import JSONResponse
from backend.exceptions import CevonDocsError, ModerationFailure, ConfigurationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("cevondocs")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    Path(config.UPLOAD_DIR).mkdir(exist_ok=True)

    if config.AI_PROVIDER == "openai":
        active_model = config.OPENAI_MODEL
    elif config.AI_PROVIDER == "gemini":
        active_model = config.GEMINI_MODEL
    elif config.AI_PROVIDER == "groq":
        active_model = config.GROQ_MODEL
    else:
        active_model = "unknown"

    logger.info("---------------------------------")
    logger.info("CevonDocs starting")
    logger.info(f"Provider : {config.AI_PROVIDER}")
    logger.info(f"Model    : {active_model}")
    logger.info("---------------------------------")
    yield


app = FastAPI(
    title="CevonDocs",
    description="AI-Powered Document Intelligence Platform",
    version=config.APP_VERSION,
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "name": "CevonDocs",
        "description": "AI-Powered Document Intelligence Platform",
        "tagline": "Extract. Validate. Structure.",
        "version": config.APP_VERSION,
        "docs_url": "/docs"
    }


@app.exception_handler(CevonDocsError)
async def cevondocs_exception_handler(request, exc: CevonDocsError):
    logger.error(f"CevonDocs exception caught [{exc.__class__.__name__}]: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_type": exc.__class__.__name__, "details": exc.details}
    )


@app.get("/health")
def health():
    db_status = "connected"
    try:
        db.init_db()
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        db_status = "disconnected"

    if config.AI_PROVIDER == "openai":
        active_model = config.OPENAI_MODEL
    elif config.AI_PROVIDER == "gemini":
        active_model = config.GEMINI_MODEL
    elif config.AI_PROVIDER == "groq":
        active_model = config.GROQ_MODEL
    else:
        active_model = "unknown"

    return {
        "status": "ok",
        "database": db_status,
        "ai_provider": config.AI_PROVIDER,
        "active_model": active_model,
        "moderation_provider": config.MODERATION_PROVIDER,
        "version": config.APP_VERSION
    }


@app.get("/metrics")
def get_metrics():
    """Exposes Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    allowed_exts = {".jpg", ".jpeg", ".png"}
    allowed_mime_types = {"image/jpeg", "image/jpg", "image/png"}

    if ext not in allowed_exts and file.content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPG and PNG images are allowed."
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    # Max file size limit: 10 MB
    max_bytes = 10 * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum upload size is 10 MB."
        )

    # Convert to base64 for moderation gate & vision extraction
    b64_image = utils.image_to_base64(image_bytes)

    # 1. Moderation Gate & Moderation Latency Measurement
    t_mod_start = time.time()
    mod_unavailable = False
    mod_status = "PASSED"
    try:
        mod_res = moderation.check_moderation(b64_image)
        is_safe, blocked_reason = mod_res[0], mod_res[1]
        mod_status = getattr(mod_res, "moderation_status", "PASSED")
    except ModerationUnavailableError as e:
        logger.warning(f"Moderation provider unavailable ({e.message}). Routing document to Manual Review.")
        is_safe = True
        blocked_reason = None
        mod_unavailable = True
        mod_status = "UNAVAILABLE"
    except ValueError as e:
        logger.error(f"Moderation gate configuration error: {e}")
        metrics.documents_processed_total.labels(status="failed").inc()
        raise ConfigurationError(f"Moderation configuration error: {e}")
    except Exception as e:
        logger.error(f"Moderation gate failed: {e}")
        metrics.documents_processed_total.labels(status="failed").inc()
        raise

    t_mod_elapsed = time.time() - t_mod_start
    metrics.moderation_latency.observe(t_mod_elapsed)

    if not is_safe:
        metrics.documents_processed_total.labels(status="blocked").inc()
        raise ModerationFailure(reason=blocked_reason or "content_flagged", provider=config.MODERATION_PROVIDER)

    # 2. Save Uploaded Image
    doc_id = utils.generate_id()
    saved_path = utils.save_upload(image_bytes, Path(config.UPLOAD_DIR), doc_id, filename)
    logger.info(f"Ingested file '{filename}' as doc_id '{doc_id}' at {saved_path}")

    # 3. Apply Watermark Provenance Stamp (saved separately as watermarked.png)
    watermarked_path = Path(config.UPLOAD_DIR) / doc_id / "watermarked.png"
    watermark.watermark_image(saved_path, doc_id, watermarked_path)

    # 4. Vision Extraction via Provider Router & Extraction Latency Measurement
    extracted_data_dict = None
    status = "auto_approved"
    flagged_fields = []

    t_ext_start = time.time()
    try:
        extracted_schema, usage = extraction.extract_invoice(b64_image)
        t_ext_elapsed = time.time() - t_ext_start
        metrics.extraction_latency.observe(t_ext_elapsed)

        # Record token cost metric
        total_tokens = usage.get("total_tokens", 0) if usage else 0
        cost_usd = total_tokens * config.COST_PER_TOKEN
        metrics.token_cost_total.inc(cost_usd)

        extracted_data_dict = extracted_schema.model_dump()

        # 5. Confidence Routing
        status, flagged_fields = confidence.route_document(extracted_schema, config.REVIEW_THRESHOLD)
        
        # If moderation provider was unavailable, force route to manual review
        if mod_unavailable or mod_status == "UNAVAILABLE":
            status = "pending_review"
            if "moderation_unavailable" not in flagged_fields:
                flagged_fields.append("moderation_unavailable")

        # Inject moderation status into validation metadata
        if "_validation" not in extracted_data_dict or not isinstance(extracted_data_dict["_validation"], dict):
            extracted_data_dict["_validation"] = {}
        extracted_data_dict["_validation"]["moderation_status"] = mod_status
        if mod_status == "LOCAL_ONLY":
            if "passed_checks" not in extracted_data_dict["_validation"]:
                extracted_data_dict["_validation"]["passed_checks"] = []
            extracted_data_dict["_validation"]["passed_checks"].append(
                "Local basic image validation passed (no AI moderation provider configured)"
            )
        elif mod_status == "UNAVAILABLE":
            if "failed_checks" not in extracted_data_dict["_validation"]:
                extracted_data_dict["_validation"]["failed_checks"] = []
            extracted_data_dict["_validation"]["failed_checks"].append(
                "Moderation provider unavailable (routed to manual review)"
            )

        logger.info(
            f"Extraction completed for doc '{doc_id}'. Provider: '{config.AI_PROVIDER}', "
            f"Latency: {t_ext_elapsed:.3f}s, Total Tokens: {total_tokens}, Status: '{status}'"
        )
    except CevonDocsError:
        metrics.documents_processed_total.labels(status="failed").inc()
        raise
    except Exception as e:
        logger.error(f"Extraction failed for doc {doc_id}: {e}")
        metrics.documents_processed_total.labels(status="failed").inc()
        raise

    # Record status metrics
    metrics.documents_processed_total.labels(status=status).inc()
    if status == "auto_approved":
        metrics.auto_approvals_total.inc()
    elif status == "pending_review":
        metrics.reviews_total.inc()

    # 6. PII Redaction before Logging
    created_at = utils.now_iso()
    extracted_json_str = json.dumps(extracted_data_dict) if extracted_data_dict else None
    if extracted_json_str:
        logger.info(f"Extracted payload for doc '{doc_id}': {pii.redact_pii(extracted_json_str)}")

    # 7. SQLite Persistence
    db.insert_document(
        doc_id=doc_id,
        filename=filename,
        status=status,
        extracted_json=extracted_json_str,
        created_at=created_at,
    )

    return IngestResponse(
        document_id=doc_id,
        status=status,
        extracted_data=extracted_data_dict,
        flagged_fields=flagged_fields
    )


@app.get("/history")
def history(limit: int = 50):
    """
    Returns the extraction history for all processed documents.
    Replaces direct SQLite access from the Streamlit frontend.
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, filename, status, created_at, extracted_json FROM documents ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = [dict(r) for r in cursor.fetchall()]

    result = []
    for r in rows:
        ext_dict = json.loads(r["extracted_json"]) if r.get("extracted_json") else {}
        val_meta = ext_dict.get("_validation", {}) if isinstance(ext_dict, dict) else {}
        final_conf = val_meta.get("final_confidence", ext_dict.get("overall_confidence", 0.0))
        result.append({
            "id": r["id"],
            "filename": r["filename"],
            "status": r["status"],
            "created_at": r["created_at"],
            "vendor": ext_dict.get("vendor") or "",
            "total": float(ext_dict.get("total") or 0.0),
            "currency": ext_dict.get("currency") or "USD",
            "final_confidence": round(float(final_conf), 4),
        })

    return {"documents": result, "count": len(result)}


@app.get("/review", response_model=ReviewResponse)
def review(document_id: Optional[str] = None):
    """
    Returns pending review documents.
    Derives flagged fields at query time via confidence.route_document.
    """
    if document_id:
        doc = db.get_document(document_id)
        rows = [doc] if doc and doc.get("status") == "pending_review" else []
    else:
        rows = db.get_pending()

    review_items = []
    for r in rows:
        extracted_json = json.loads(r["extracted_json"]) if r.get("extracted_json") else {}
        _, flagged = confidence.route_document(extracted_json, config.REVIEW_THRESHOLD)
        review_items.append(
            ReviewItem(
                document_id=r["id"],
                filename=r["filename"],
                status=r["status"],
                extracted_json=extracted_json,
                flagged_fields=flagged,
                created_at=r["created_at"],
            )
        )

    return ReviewResponse(documents=review_items)


@app.post("/approve", response_model=ApproveResponse)
def approve(req: ApproveRequest):
    """
    Approves a document pending review with human-corrected fields.
    """
    existing = db.get_document(req.document_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Document '{req.document_id}' not found.")

    reviewed_json_str = json.dumps(req.reviewed_data)
    success = db.approve_document(req.document_id, reviewed_json_str)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to approve document in database.")

    # PII Redacted Logging
    logger.info(
        f"Approved document '{req.document_id}'. Reviewed Data: {pii.redact_pii(reviewed_json_str)}"
    )

    return ApproveResponse(
        document_id=req.document_id,
        status="approved",
        message="Document reviewed and approved successfully."
    )
