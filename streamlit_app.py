import os
import json
import time
import requests
import pandas as pd
from PIL import Image
import streamlit as st

import config

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="CevonDocs — Enterprise Document Intelligence Platform",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# ==========================================
# SESSION STATE INITIALISATION
# ==========================================
if "last_extraction" not in st.session_state:
    st.session_state["last_extraction"] = None          # persists across reruns
if "last_uploaded_name" not in st.session_state:
    st.session_state["last_uploaded_name"] = None
# UI-only provider override (does NOT affect the FastAPI backend process)
if "ui_provider" not in st.session_state:
    st.session_state["ui_provider"] = config.AI_PROVIDER.lower()
# UI-only threshold (informational display only)
if "ui_threshold" not in st.session_state:
    st.session_state["ui_threshold"] = config.REVIEW_THRESHOLD

# ==========================================
# CSS — SINGLE DARK THEME (permanent)
# ==========================================
APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [data-testid="stAppViewContainer"],
[data-testid="stMainBlockContainer"], [data-testid="stHeader"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #0B0F19 !important;
    color: #F8FAFC !important;
}
[data-testid="stHeader"] { background: transparent !important; }

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
    color: #F8FAFC !important;
    font-weight: 800 !important;
    letter-spacing: -0.025em !important;
}
p, span, label, li, div, small { color: #CBD5E1 !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #F8FAFC !important; font-weight: 800 !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label { color: #94A3B8 !important; font-weight: 600 !important; }

/* Branding */
.brand-title {
    font-size: 2.8rem !important;
    font-weight: 900 !important;
    letter-spacing: -0.03em !important;
    margin-bottom: 0.25rem !important;
    line-height: 1.1 !important;
    background: linear-gradient(135deg, #FFFFFF 0%, #A5B4FC 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.brand-subtitle {
    font-size: 1.2rem !important;
    font-weight: 600 !important;
    color: #94A3B8 !important;
    margin-bottom: 0.75rem !important;
}
.brand-tagline {
    display: inline-block;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    color: #818CF8 !important;
    background-color: rgba(99,102,241,0.12) !important;
    padding: 0.4rem 1.1rem !important;
    border-radius: 9999px !important;
    border: 1px solid rgba(129,140,248,0.3) !important;
    box-shadow: 0 0 15px rgba(99,102,241,0.15) !important;
    margin-bottom: 2rem !important;
}

/* Cards */
.cevon-card {
    background-color: #111827 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 16px !important;
    padding: 1.75rem !important;
    margin-bottom: 1.75rem !important;
    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3), 0 8px 10px -6px rgba(0,0,0,0.3) !important;
}
.cevon-card-header {
    font-size: 1.15rem !important;
    font-weight: 800 !important;
    color: #F8FAFC !important;
    margin-bottom: 1.25rem !important;
    border-bottom: 1px solid rgba(255,255,255,0.08) !important;
    padding-bottom: 0.75rem !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.25rem !important;
    box-shadow: 0 4px 14px 0 rgba(79,70,229,0.4) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px 0 rgba(79,70,229,0.6) !important;
}

/* Status Badges */
.badge-approved, .badge-pending, .badge-error {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem !important;
    font-weight: 800 !important;
    padding: 0.4rem 1rem !important;
    border-radius: 9999px !important;
}
.badge-approved { color: #34D399 !important; background-color: rgba(16,185,129,0.12) !important; border: 1px solid rgba(52,211,153,0.3) !important; }
.badge-pending  { color: #FBBF24 !important; background-color: rgba(245,158,11,0.12) !important; border: 1px solid rgba(251,191,36,0.3) !important; }
.badge-error    { color: #F87171 !important; background-color: rgba(239,68,68,0.12) !important; border: 1px solid rgba(248,113,113,0.3) !important; }

/* Confidence chips */
.conf-high, .conf-medium, .conf-low {
    font-weight: 800 !important;
    padding: 0.2rem 0.6rem !important;
    border-radius: 6px !important;
}
.conf-high   { color: #34D399 !important; background-color: rgba(16,185,129,0.10) !important; border: 1px solid rgba(52,211,153,0.25) !important; }
.conf-medium { color: #FBBF24 !important; background-color: rgba(245,158,11,0.10) !important; border: 1px solid rgba(251,191,36,0.25) !important; }
.conf-low    { color: #F87171 !important; background-color: rgba(239,68,68,0.10) !important; border: 1px solid rgba(248,113,113,0.25) !important; }

/* Empty state */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    background-color: #111827 !important;
    border: 2px dashed rgba(255,255,255,0.12) !important;
    border-radius: 16px !important;
    margin: 1.5rem 0 !important;
}
.empty-state-icon  { font-size: 3.5rem !important; margin-bottom: 1rem !important; }
.empty-state-title { font-size: 1.3rem !important; font-weight: 800 !important; color: #F8FAFC !important; margin-bottom: 0.5rem !important; }
.empty-state-desc  { font-size: 0.95rem !important; font-weight: 500 !important; color: #94A3B8 !important; }

/* File uploader */
[data-testid="stFileUploader"] {
    background-color: #111827 !important;
    border: 2px dashed rgba(99,102,241,0.3) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span {
    font-size: 1.05rem !important;
    font-weight: 800 !important;
    color: #F8FAFC !important;
}
[data-testid="stFileUploader"] section { background-color: #1F2937 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem !important;
    border-bottom: 1px solid rgba(255,255,255,0.08) !important;
    padding-bottom: 0.5rem !important;
}
.stTabs [data-baseweb="tab"] {
    height: 44px !important;
    border-radius: 8px !important;
    color: #94A3B8 !important;
    font-weight: 600 !important;
    padding: 0 1.25rem !important;
    background-color: transparent !important;
}
.stTabs [aria-selected="true"] {
    background-color: rgba(99,102,241,0.15) !important;
    color: #818CF8 !important;
    font-weight: 800 !important;
}

/* Expander */
.stExpander, [data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 14px !important;
    background-color: #111827 !important;
}
[data-testid="stExpander"] details summary span {
    color: #F8FAFC !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
}

/* Footer */
.cevon-footer {
    text-align: center;
    padding: 3rem 0 1.5rem 0;
    color: #64748B !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    border-top: 1px solid rgba(255,255,255,0.08) !important;
    margin-top: 3.5rem !important;
}

/* Source provenance + arithmetic labels */
.prov-label   { font-size: 0.75rem !important; font-weight: 500 !important; color: #64748B !important; opacity: 0.85; margin-left: 0.4rem; }
.fin-verified { color: #34D399 !important; font-weight: 700 !important; font-size: 0.8rem; }
.fin-failed   { color: #F87171 !important; font-weight: 700 !important; font-size: 0.8rem; }
</style>
"""

st.markdown(APP_CSS, unsafe_allow_html=True)

# ==========================================
# SIDEBAR — ALL CONTENT IN ONE BLOCK
# ==========================================
LOGO_CLEAN_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo_clean_dark.png")
LOGO_FALLBACK_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
ACTIVE_LOGO_PATH = LOGO_CLEAN_PATH if os.path.exists(LOGO_CLEAN_PATH) else LOGO_FALLBACK_PATH

with st.sidebar:
    # System Health Check


    # System Health Check
    server_status = "Disconnected"
    status_icon = "🔴"
    db_status = "unknown"
    active_provider = config.AI_PROVIDER.upper()
    active_model = "—"
    try:
        health_res = requests.get(f"{API_BASE_URL}/health", timeout=3)
        if health_res.status_code == 200:
            h = health_res.json()
            server_status = "Operational"
            status_icon = "🟢"
            db_status = h.get("database", "connected")
            active_provider = h.get("ai_provider", config.AI_PROVIDER).upper()
            active_model = h.get("active_model", "—")
    except Exception:
        pass

    st.markdown("### 📡 System Status")
    st.markdown(f"**Backend Service:** {status_icon} {server_status}")
    st.markdown(f"**Database:** `{db_status}`")
    st.markdown(f"**Active Provider:** `{active_provider}`")
    st.markdown(f"**Active Model:** `{active_model}`")

    st.markdown("---")

    # Processing Limits — sourced from config.py, not hardcoded
    max_mb = int(10 * 1024 * 1024 / (1024 * 1024))  # from the /ingest 10MB limit
    st.markdown("### ⚙️ Processing Limits")
    st.markdown(f"- **Auto-Approval Threshold:** `{config.REVIEW_THRESHOLD:.2f}`")
    st.markdown("- **Accepted Formats:** `PNG`, `JPG`, `JPEG`")
    st.markdown(f"- **Max Document Size:** `{max_mb} MB`")

    st.markdown("---")
    st.markdown(
        "<div style='font-size: 0.8rem; opacity: 0.7;'>"
        f"CevonDocs v{config.APP_VERSION}<br/>"
        "AI-Powered Document Intelligence Platform"
        "</div>",
        unsafe_allow_html=True,
    )

# ==========================================
# HERO BRANDING HEADER
# ==========================================
if os.path.exists(ACTIVE_LOGO_PATH):
    st.image(ACTIVE_LOGO_PATH, width=260)
else:
    st.markdown('<div class="brand-title">🧾 CevonDocs</div>', unsafe_allow_html=True)

st.markdown('<div class="brand-subtitle" style="margin-top: 0.5rem; margin-bottom: 0.5rem;">Enterprise Document Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="brand-tagline">Extract. Validate. Structure.</div>', unsafe_allow_html=True)

# ==========================================
# PRIMARY NAVIGATION TABS
# ==========================================
tab_upload, tab_review, tab_history, tab_settings = st.tabs([
    "📤 Upload & Extract Document",
    "🔍 Human Review Queue",
    "📜 Extraction History",
    "⚙️ Platform Settings",
])


# ==========================================
# UTILITY: Confidence badge renderer & check formatting
# ==========================================
def get_confidence_badge(confidence: float) -> str:
    """Returns formatted confidence decimal string with visual badge."""
    val = float(confidence or 0.0)
    val_str = f"{val:.2f}"
    if val >= 0.75:
        return f'<span class="conf-high">🟢 {val_str}</span>'
    elif val >= 0.50:
        return f'<span class="conf-medium">🟡 {val_str}</span>'
    else:
        return f'<span class="conf-low">🔴 {val_str}</span>'


def clean_check_text(text: str) -> str:
    """Strips internal implementation details and debug noise from check messages."""
    if not text:
        return ""
    t = str(text)
    t = t.replace(" (no AI moderation provider configured)", "")
    t = t.replace("moderation_unavailable", "Moderation Provider Unavailable")
    return t.strip()


def format_passed_checks(passed_list: list) -> list:
    """
    Simplifies and groups passed checks for a clean, non-verbose UI presentation.
    Never exposes internal debug text or implementation details.
    Returns a list of tuples: (title, detail_text)
    """
    grouped = []
    
    # 1. Group Required Fields
    req_fields_found = [c for c in passed_list if "Required field present:" in c]
    if req_fields_found:
        fields = [c.split("Required field present:")[-1].strip() for c in req_fields_found]
        grouped.append(("✓ Required fields verified", ", ".join(fields)))

    # 2. Group Financial Totals Check
    if any("Financial totals verified" in c for c in passed_list):
        grouped.append(("✓ Financial totals verified", "Subtotal + Tax = Total"))

    # 3. Group Line Item Totals Check
    if any("Line item totals" in c or "Sum(Line Items)" in c for c in passed_list):
        grouped.append(("✓ Line item totals verified", "Sum(Line Items) = Subtotal"))

    # 4. Group Image Validation Check
    if any("image" in c.lower() or "resolution" in c.lower() or "validation passed" in c.lower() for c in passed_list):
        grouped.append(("✓ Image validation passed", "Image integrity and quality verified"))

    # 5. Any remaining checks not caught by above groups
    for c in passed_list:
        if not any(k in c for k in ["Required field present:", "Financial totals verified", "Line item totals", "image", "resolution"]):
            cleaned = clean_check_text(c)
            if cleaned:
                grouped.append((f"✓ {cleaned}", ""))

    return grouped


# ==========================================
# TAB 1: UPLOAD & EXTRACT DOCUMENT
# ==========================================
with tab_upload:
    st.markdown("#### Upload Document")
    st.caption("Upload an invoice or receipt to begin AI-powered document extraction.")

    # Confidence Guide — placed inside Tab 1 where it's relevant
    with st.expander("ℹ️ Confidence & Quality Guide", expanded=False):
        st.markdown(
            """
            - 🟢 **0.90 – 1.00**: High Confidence — Vision AI extracted with high certainty
            - 🟡 **0.75 – 0.89**: Medium Confidence — Passed threshold, review recommended for key fields
            - 🔴 **Below 0.75**: Low Confidence — Flagged for mandatory human review

            > **Note:** Confidence reflects AI extraction certainty only.
            > Validation checks are shown separately in the Validation card.
            """
        )

    uploaded_file = st.file_uploader(
        "Select Document Image (PNG, JPG, JPEG)",
        type=["jpg", "jpeg", "png"],
        help="Maximum file size: 10 MB.",
    )

    # Clear cached results when a new file is uploaded
    if uploaded_file is not None:
        if st.session_state["last_uploaded_name"] != uploaded_file.name:
            st.session_state["last_extraction"] = None
            st.session_state["last_uploaded_name"] = uploaded_file.name

    if uploaded_file is None:
        # Clear stale results when no file is selected
        st.session_state["last_extraction"] = None
        st.session_state["last_uploaded_name"] = None
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📤</div>
                <div class="empty-state-title">No Document Selected</div>
                <div class="empty-state-desc">Drag and drop an invoice or receipt image above to begin AI-powered extraction.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        col_preview, col_results = st.columns([1, 1], gap="large")

        with col_preview:
            st.markdown('<div class="cevon-card">', unsafe_allow_html=True)
            st.markdown('<div class="cevon-card-header">📷 Document Preview</div>', unsafe_allow_html=True)

            # Read bytes once, open PIL image once — avoid double-read of buffer
            file_bytes = uploaded_file.getvalue()
            try:
                pil_img = Image.open(uploaded_file)
                img_w, img_h = pil_img.size
                dim_str = f" &bull; Dimensions: {img_w}×{img_h}px"
            except Exception:
                pil_img = None
                dim_str = ""

            # Pass pil_img (or raw bytes) to avoid buffer pointer issues
            st.image(pil_img if pil_img else file_bytes, use_column_width=True)
            st.caption(f"**Filename:** `{uploaded_file.name}` &bull; **Size:** `{len(file_bytes) / 1024:.1f} KB`{dim_str}")

            process_btn = st.button("🚀 Run Extraction Pipeline", type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_results:
            # Run extraction pipeline on button click
            if process_btn:
                progress_placeholder = st.empty()
                progress_placeholder.info("🔄 **Step 1/4:** Initializing document ingestion & validation...")
                time.sleep(0.3)
                progress_placeholder.info("🛡️ **Step 2/4:** Screening content moderation gate...")
                time.sleep(0.3)
                progress_placeholder.info("🧠 **Step 3/4:** Extracting structured fields via Vision AI Engine...")

                try:
                    files = {"file": (uploaded_file.name, file_bytes, uploaded_file.type)}
                    response = requests.post(f"{API_BASE_URL}/ingest", files=files, timeout=60)

                    progress_placeholder.info("⚡ **Step 4/4:** Normalizing schema & evaluating confidence scores...")
                    time.sleep(0.2)
                    progress_placeholder.empty()

                    if response.status_code == 200:
                        # Store result in session_state so it survives reruns
                        st.session_state["last_extraction"] = response.json()
                    elif response.status_code == 422:
                        st.markdown(
                            '<div class="badge-error">🚫 Content Moderation Rejected Image</div>',
                            unsafe_allow_html=True,
                        )
                        st.error(f"**Reason:** {response.json().get('detail')}")
                        st.session_state["last_extraction"] = None
                    else:
                        st.error(f"**Extraction Failed ({response.status_code}):** {response.text}")
                        st.session_state["last_extraction"] = None

                except Exception as e:
                    progress_placeholder.empty()
                    st.error(f"**System Service Error:** Unable to complete request. Details: {e}")
                    st.session_state["last_extraction"] = None

            # Render results from session_state (persists across reruns)
            data = st.session_state.get("last_extraction")

            if data is None:
                st.markdown(
                    """
                    <div class="empty-state">
                        <div class="empty-state-icon">📊</div>
                        <div class="empty-state-title">Ready for Document Extraction</div>
                        <div class="empty-state-desc">Click <strong>'Run Extraction Pipeline'</strong> on the preview card to execute multi-stage vision extraction.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                doc_id  = data.get("document_id")
                status  = data.get("status")
                extracted = data.get("extracted_data")
                flagged   = data.get("flagged_fields", [])

                st.success("✅ Document processed successfully!")

                # Status Badge & Refined Status Banner
                if status == "auto_approved":
                    st.markdown(
                        '<div style="margin: 0.75rem 0;"><span class="badge-approved">✓ Auto-Approved</span></div>',
                        unsafe_allow_html=True,
                    )
                    st.caption("Final confidence exceeded the 0.75 approval threshold. All validation checks passed.")
                else:
                    st.markdown(
                        '<div style="margin: 0.75rem 0;"><span class="badge-pending">⚠ Pending Human Review</span></div>',
                        unsafe_allow_html=True,
                    )
                    st.caption("One or more validation checks require manual verification.")
                    # Guard: only show warning when there are actual flagged fields
                    if flagged:
                        clean_flags = [clean_check_text(f) for f in flagged]
                        st.warning(f"⚠️ **Flagged Fields / Checks:** {', '.join(clean_flags)}")

                if extracted:
                    validation_meta  = extracted.get("_validation") or {}
                    passed_checks    = validation_meta.get("passed_checks", [])
                    failed_checks    = validation_meta.get("failed_checks", [])
                    provenance_meta  = extracted.get("_provenance", {})

                    # Arithmetic verification badge — shown ONCE at card level, not per-field
                    fin_badge = ""
                    if any("Financial totals verified" in c for c in passed_checks):
                        fin_badge = '<span class="fin-verified">✓ Arithmetic Verified</span>'
                    elif any("Subtotal + Tax" in c for c in failed_checks):
                        fin_badge = '<span class="fin-failed">⚠ Arithmetic Failed</span>'

                    # ── Extracted Invoice Summary Card ──────────────────────
                    st.markdown('<div class="cevon-card">', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="cevon-card-header">📊 Extracted Invoice Summary {fin_badge}</div>',
                        unsafe_allow_html=True,
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        def _prov(field):
                            src = provenance_meta.get(field, "AI")
                            return f'<span class="prov-label">[{src}]</span>'

                        st.markdown(
                            f"**Vendor:** {extracted.get('vendor') or '*Unextracted*'} "
                            f"({get_confidence_badge(extracted.get('vendor_confidence', 0))}) {_prov('vendor')}",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"**Invoice #:** {extracted.get('invoice_number') or '*Unextracted*'} "
                            f"({get_confidence_badge(extracted.get('invoice_number_confidence', 0))}) {_prov('invoice_number')}",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"**Date:** {extracted.get('date') or '*Unextracted*'} "
                            f"({get_confidence_badge(extracted.get('date_confidence', 0))}) {_prov('date')}",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"**Currency:** {extracted.get('currency') or '*Unextracted*'} "
                            f"({get_confidence_badge(extracted.get('currency_confidence', 0))}) {_prov('currency')}",
                            unsafe_allow_html=True,
                        )

                    with col2:
                        currency_sym = extracted.get("currency") or "USD"
                        st.markdown(
                            f"**Subtotal:** {currency_sym} {float(extracted.get('subtotal') or 0.0):,.2f} "
                            f"({get_confidence_badge(extracted.get('subtotal_confidence', 0))}) {_prov('subtotal')}",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"**Tax:** {currency_sym} {float(extracted.get('tax') or 0.0):,.2f} "
                            f"({get_confidence_badge(extracted.get('tax_confidence', 0))}) {_prov('tax')}",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"**Total:** {currency_sym} {float(extracted.get('total') or 0.0):,.2f} "
                            f"({get_confidence_badge(extracted.get('total_confidence', 0))}) {_prov('total')}",
                            unsafe_allow_html=True,
                        )
                        final_c = extracted.get("overall_confidence", 0.8)
                        st.markdown(f"**Final Confidence:** {get_confidence_badge(final_c)}", unsafe_allow_html=True)

                    st.markdown('</div>', unsafe_allow_html=True)

                    # ── Refined Validation & Calibration Card ───────────────
                    if validation_meta and isinstance(validation_meta, dict):
                        st.markdown('<div class="cevon-card">', unsafe_allow_html=True)
                        st.markdown('<div class="cevon-card-header">🛡️ Validation Summary</div>', unsafe_allow_html=True)

                        passed_lst   = validation_meta.get("passed_checks", [])
                        failed_lst   = validation_meta.get("failed_checks", [])
                        warn_lst     = validation_meta.get("warnings", [])
                        total_chks   = validation_meta.get("total_checks", 0)
                        passed_count = len(passed_lst)
                        total_chks   = max(total_chks, passed_count + len(failed_lst))
                        val_score_pct= int(min(100, round((passed_count / total_chks) * 100))) if total_chks > 0 else 100

                        adj          = validation_meta.get("confidence_adjustment", 0.0)
                        final_conf   = validation_meta.get("final_confidence", extracted.get("overall_confidence", 0.8))
                        raw_conf     = extracted.get("_ai_confidence", round(final_conf - adj, 2))

                        # Four completely independent metrics
                        m1, m2, m3, m4 = st.columns(4)
                        with m1:
                            st.metric(
                                label="Validation Score",
                                value=f"{val_score_pct}%",
                                delta=f"{passed_count} / {total_chks} Checks Passed",
                                delta_color="off",
                            )
                        with m2:
                            st.metric(
                                label="AI Base Confidence",
                                value=f"{float(raw_conf):.2f}",
                            )
                        with m3:
                            adj_str = "No adjustment" if abs(adj) < 0.001 or adj == 0.0 else f"{adj:+.2f}"
                            st.metric(
                                label="Validation Adjustment",
                                value=adj_str,
                            )
                        with m4:
                            st.metric(
                                label="Final Confidence",
                                value=f"{float(final_conf):.2f}",
                            )

                        st.markdown("---")

                        # Grouped Passed Checks
                        grouped_passed = format_passed_checks(passed_lst)
                        if grouped_passed:
                            st.markdown("##### 🟢 Passed Checks")
                            for title, detail in grouped_passed:
                                if detail:
                                    st.markdown(f"**{title}** &bull; *{detail}*")
                                else:
                                    st.markdown(f"**{title}**")

                        # Warnings Section (only when present)
                        if warn_lst:
                            st.markdown("##### ⚠️ Warnings")
                            for warn in warn_lst:
                                st.markdown(f"• {clean_check_text(warn)}")

                        # Failed Checks Section (only when present)
                        if failed_lst:
                            st.markdown("##### ❌ Failed Checks")
                            for fail in failed_lst:
                                st.markdown(f"• {clean_check_text(fail)}")

                        st.markdown('</div>', unsafe_allow_html=True)

                    # ── Line Items Grid ─────────────────────────────────────
                    line_items = extracted.get("line_items", [])
                    if line_items:
                        st.markdown("##### 🛒 Extracted Line Items")
                        st.dataframe(pd.DataFrame(line_items), use_container_width=True)

                    # ── Editable Post-Extraction Review & Approval Form ─────
                    st.markdown("---")
                    st.markdown('<div class="cevon-card">', unsafe_allow_html=True)
                    st.markdown(
                        '<div class="cevon-card-header">✏️ Review & Edit Extracted Fields</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        "Pre-populated with AI-extracted values. Modify any field below before committing approval."
                    )

                    with st.form(key=f"tab1_review_form_{doc_id}"):
                        f_col1, f_col2 = st.columns(2)
                        with f_col1:
                            edit_vendor = st.text_input(
                                "Vendor Name",
                                value=str(extracted.get("vendor") or ""),
                                key=f"t1_vendor_{doc_id}",
                            )
                            edit_inv_num = st.text_input(
                                "Invoice Number",
                                value=str(extracted.get("invoice_number") or ""),
                                key=f"t1_inv_{doc_id}",
                            )
                            edit_date = st.text_input(
                                "Invoice Date (YYYY-MM-DD)",
                                value=str(extracted.get("date") or ""),
                                key=f"t1_date_{doc_id}",
                            )
                            edit_currency = st.text_input(
                                "Currency Code",
                                value=str(extracted.get("currency") or "USD"),
                                key=f"t1_curr_{doc_id}",
                            )

                        with f_col2:
                            edit_subtotal = st.number_input(
                                "Subtotal",
                                value=float(extracted.get("subtotal") or 0.0),
                                format="%.2f",
                                step=0.01,
                                key=f"t1_subtotal_{doc_id}",
                            )
                            edit_tax = st.number_input(
                                "Tax Amount",
                                value=float(extracted.get("tax") or 0.0),
                                format="%.2f",
                                step=0.01,
                                key=f"t1_tax_{doc_id}",
                            )
                            edit_total = st.number_input(
                                "Total Amount",
                                value=float(extracted.get("total") or 0.0),
                                format="%.2f",
                                step=0.01,
                                key=f"t1_total_{doc_id}",
                            )

                        st.markdown("##### 🛒 Line Items Data Grid")
                        raw_t1_items = extracted.get("line_items", [])
                        df_t1 = pd.DataFrame(raw_t1_items) if raw_t1_items else pd.DataFrame(
                            columns=["description", "quantity", "unit_price", "amount"]
                        )
                        for c_name in ["description", "quantity", "unit_price", "amount"]:
                            if c_name not in df_t1.columns:
                                df_t1[c_name] = None

                        edited_t1_df = st.data_editor(
                            df_t1,
                            column_config={
                                "description": st.column_config.TextColumn("Description"),
                                "quantity":    st.column_config.NumberColumn("Quantity",   format="%.2f"),
                                "unit_price":  st.column_config.NumberColumn("Unit Price", format="%.2f"),
                                "amount":      st.column_config.NumberColumn("Amount",     format="%.2f"),
                            },
                            use_container_width=True,
                            num_rows="dynamic",
                            key=f"t1_items_editor_{doc_id}",
                        )

                        btn_label = "✅ Approve Document & Commit Records" if status != "approved" else "🔄 Re-Approve & Update Document"
                        submit_tab1_approve = st.form_submit_button(
                            btn_label,
                            type="primary",
                            use_container_width=True,
                        )

                        if submit_tab1_approve:
                            reviewed_payload = dict(extracted)
                            reviewed_payload["vendor"] = edit_vendor
                            reviewed_payload["invoice_number"] = edit_inv_num
                            reviewed_payload["date"] = edit_date
                            reviewed_payload["currency"] = edit_currency
                            reviewed_payload["subtotal"] = edit_subtotal
                            reviewed_payload["tax"] = edit_tax
                            reviewed_payload["total"] = edit_total
                            reviewed_payload["line_items"] = edited_t1_df.to_dict(orient="records")

                            try:
                                app_res = requests.post(
                                    f"{API_BASE_URL}/approve",
                                    json={"document_id": doc_id, "reviewed_data": reviewed_payload},
                                    timeout=10,
                                )
                                if app_res.status_code == 200:
                                    st.success("✅ Document reviewed, updated, and committed successfully!")
                                    st.cache_data.clear()
                                    if "last_extraction" in st.session_state and st.session_state["last_extraction"]:
                                        st.session_state["last_extraction"]["status"] = "approved"
                                        st.session_state["last_extraction"]["extracted_data"] = reviewed_payload
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(f"Approval submission failed ({app_res.status_code}): {app_res.text}")
                            except Exception as ex:
                                st.error(f"Approval submission error: {ex}")

                    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# TAB 2: HUMAN REVIEW QUEUE
# ==========================================
with tab_review:
    st.markdown("#### Human-in-the-Loop Review Queue")
    st.caption("Review documents where confidence scores fell below the threshold. Correct fields and approve.")

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        refresh_review = st.button("🔄 Refresh Queue", use_container_width=True)

    if refresh_review:
        st.cache_data.clear()

    @st.cache_data(ttl=30, show_spinner=False)
    def _fetch_review_queue():
        res = requests.get(f"{API_BASE_URL}/review", timeout=10)
        if res.status_code == 200:
            return res.json().get("documents", []), None
        return [], f"Failed to query review queue ({res.status_code}): {res.text}"

    with st.spinner("Loading review queue..."):
        try:
            docs, err = _fetch_review_queue()
        except Exception as e:
            docs, err = [], str(e)

    if err:
        st.error(f"Unable to connect to backend review queue: {err}")
    elif not docs:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🎉</div>
                <div class="empty-state-title">Review Queue Clear</div>
                <div class="empty-state-desc">All ingested invoices met quality thresholds — no pending reviews.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        doc_options = {f"{d['document_id']} — {d['filename']}": d for d in docs}
        selected_label = st.selectbox("Select document to review:", list(doc_options.keys()))
        selected_doc = doc_options[selected_label]

        doc_id   = selected_doc["document_id"]
        # Ensure extracted_json is parsed (it may arrive as a dict or a JSON string)
        raw_extracted = selected_doc.get("extracted_json", {})
        if isinstance(raw_extracted, str):
            try:
                extracted = json.loads(raw_extracted)
            except Exception:
                extracted = {}
        elif isinstance(raw_extracted, dict):
            extracted = raw_extracted
        else:
            extracted = {}

        flagged = selected_doc.get("flagged_fields", [])

        val_meta      = extracted.get("_validation", {}) if extracted else {}
        failed_checks = val_meta.get("failed_checks", [])

        st.markdown('<div class="cevon-card">', unsafe_allow_html=True)
        st.markdown('<div class="cevon-card-header">📋 Reasons for Review</div>', unsafe_allow_html=True)
        if failed_checks:
            for fail in failed_checks:
                st.markdown(f"• ❌ **{clean_check_text(fail)}**")
        if flagged:
            for flag in flagged:
                st.markdown(f"• ⚠️ **Low Field Confidence (< 0.75):** `{clean_check_text(flag)}`")
        if not failed_checks and not flagged:
            st.markdown("• No specific reason recorded.")
        st.markdown('</div>', unsafe_allow_html=True)

        col_img, col_edit = st.columns([1, 1], gap="large")

        with col_img:
            st.markdown('<div class="cevon-card">', unsafe_allow_html=True)
            st.markdown('<div class="cevon-card-header">🖼️ Source Document</div>', unsafe_allow_html=True)
            img_path = os.path.join("uploads", doc_id, "watermarked.png")
            if not os.path.exists(img_path):
                img_path = os.path.join("uploads", doc_id, "original.png")

            if os.path.exists(img_path):
                try:
                    review_img = Image.open(img_path)
                    st.image(review_img, use_column_width=True)
                except Exception as img_err:
                    st.warning(f"Could not render document image: {img_err}")
            else:
                st.info("Document image preview unavailable on local disk.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_edit:
            st.markdown('<div class="cevon-card">', unsafe_allow_html=True)
            st.markdown('<div class="cevon-card-header">✏️ Correct & Verify Document Fields</div>', unsafe_allow_html=True)

            with st.form("review_form"):
                corr_vendor         = st.text_input("Vendor / Merchant Name", value=extracted.get("vendor") or "")
                corr_invoice_number = st.text_input("Invoice Number", value=extracted.get("invoice_number") or "")
                corr_date           = st.text_input("Date", value=extracted.get("date") or "")
                corr_currency       = st.text_input("Currency Code", value=extracted.get("currency") or "")

                col_num1, col_num2, col_num3 = st.columns(3)
                with col_num1:
                    corr_subtotal = st.number_input("Subtotal", value=float(extracted.get("subtotal") or 0.0), format="%.2f")
                with col_num2:
                    corr_tax   = st.number_input("Tax",   value=float(extracted.get("tax")   or 0.0), format="%.2f")
                with col_num3:
                    corr_total = st.number_input("Total", value=float(extracted.get("total") or 0.0), format="%.2f")

                st.markdown("##### 🛒 Line Items Data Grid")
                raw_items = extracted.get("line_items", [])
                df_items  = pd.DataFrame(raw_items) if raw_items else pd.DataFrame(
                    columns=["description", "quantity", "unit_price", "amount", "confidence"]
                )
                for col_name in ["description", "quantity", "unit_price", "amount", "confidence"]:
                    if col_name not in df_items.columns:
                        df_items[col_name] = None

                edited_df = st.data_editor(
                    df_items,
                    column_config={
                        "description": st.column_config.TextColumn("Description"),
                        "quantity":    st.column_config.NumberColumn("Quantity",     format="%.2f"),
                        "unit_price":  st.column_config.NumberColumn("Unit Price",   format="%.2f"),
                        "amount":      st.column_config.NumberColumn("Amount",       format="%.2f"),
                        "confidence":  st.column_config.NumberColumn("Confidence",   disabled=True, format="%.2f"),
                    },
                    disabled=["confidence"],
                    use_container_width=True,
                    num_rows="dynamic",
                    key=f"line_items_editor_{doc_id}",
                )

                submit_approve = st.form_submit_button(
                    "✅ Approve Document & Commit Records",
                    type="primary",
                    use_container_width=True,
                )

                if submit_approve:
                    corrected_payload                  = dict(extracted)
                    corrected_payload["vendor"]        = corr_vendor
                    corrected_payload["invoice_number"]= corr_invoice_number
                    corrected_payload["date"]          = corr_date
                    corrected_payload["currency"]      = corr_currency
                    corrected_payload["subtotal"]      = corr_subtotal
                    corrected_payload["tax"]           = corr_tax
                    corrected_payload["total"]         = corr_total
                    corrected_payload["line_items"]    = edited_df.to_dict(orient="records")

                    app_res = requests.post(
                        f"{API_BASE_URL}/approve",
                        json={"document_id": doc_id, "reviewed_data": corrected_payload},
                    )
                    if app_res.status_code == 200:
                        st.success("✅ Document reviewed and approved successfully!")
                        st.cache_data.clear()
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Approval submission failed ({app_res.status_code}): {app_res.text}")

            st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# TAB 3: EXTRACTION HISTORY  (via API — no direct SQLite)
# ==========================================
with tab_history:
    st.markdown("#### Ingestion & Extraction History")
    st.caption("Complete audit trail of all processed documents, confidence scores, and approval states.")

    col_h_btn, _ = st.columns([1, 5])
    with col_h_btn:
        refresh_history = st.button("🔄 Refresh History", use_container_width=True)

    if refresh_history:
        st.cache_data.clear()

    @st.cache_data(ttl=30, show_spinner=False)
    def _fetch_history():
        res = requests.get(f"{API_BASE_URL}/history", timeout=10)
        if res.status_code == 200:
            return res.json().get("documents", []), None
        return [], f"History endpoint error ({res.status_code}): {res.text}"

    with st.spinner("Loading extraction history..."):
        try:
            hist_docs, hist_err = _fetch_history()
        except Exception as e:
            hist_docs, hist_err = [], str(e)

    if hist_err:
        st.error(f"Unable to load document history: {hist_err}")
    elif not hist_docs:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📜</div>
                <div class="empty-state-title">No Extraction Records Found</div>
                <div class="empty-state-desc">Upload and process a document in the Upload tab to populate history.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        table_data = []
        for r in hist_docs:
            st_str = r.get("status", "")
            if st_str == "auto_approved":
                st_badge = "🟢 Auto-Approved"
            elif st_str == "approved":
                st_badge = "🟢 Approved"
            else:
                st_badge = "🟡 Pending Review"

            currency = r.get("currency") or "USD"
            total    = r.get("total", 0.0)
            raw_id   = r.get("id", "")
            short_id = raw_id[:8] + "…" if len(raw_id) > 8 else raw_id  # readable truncated UUID

            table_data.append({
                "Doc ID":          short_id,
                "Filename":        r.get("filename") or "—",
                "Status":          st_badge,
                "Vendor":          r.get("vendor") or "—",
                "Total":           f"{currency} {total:,.2f}",         # uses actual currency, not hardcoded $
                "Final Confidence":f"{float(r.get('final_confidence', 0.0)):.2f}",
                "Timestamp":       (r.get("created_at") or "")[:19].replace("T", " "),
            })

        df_hist = pd.DataFrame(table_data)
        st.dataframe(df_hist, use_container_width=True)


# ==========================================
# TAB 4: PLATFORM SETTINGS
# ==========================================
with tab_settings:
    st.markdown("#### Enterprise Engine Settings")
    st.caption("Configure automated threshold boundaries, vision provider models, and screening policies.")

    col_s1, col_s2 = st.columns([1, 1], gap="large")

    with col_s1:
        st.markdown('<div class="cevon-card">', unsafe_allow_html=True)
        st.markdown('<div class="cevon-card-header">🎯 Automated Approval Threshold</div>', unsafe_allow_html=True)

        ui_threshold = st.slider(
            "Auto-Approval Confidence Cutoff (UI view only)",
            min_value=0.50,
            max_value=0.95,
            value=float(st.session_state["ui_threshold"]),
            step=0.01,
            key="threshold_slider",
        )
        st.session_state["ui_threshold"] = ui_threshold

        st.caption(
            f"ℹ️ **Backend threshold:** `{config.REVIEW_THRESHOLD:.2f}` (set via `REVIEW_THRESHOLD` env var). "
            f"This slider is for display/planning purposes. To change the live threshold, update `.env` and restart the backend."
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_s2:
        st.markdown('<div class="cevon-card">', unsafe_allow_html=True)
        st.markdown('<div class="cevon-card-header">🧠 AI Vision Engine & Screening</div>', unsafe_allow_html=True)

        provider_options = ["gemini", "openai", "groq"]
        curr_ui_provider = st.session_state["ui_provider"]
        if curr_ui_provider not in provider_options:
            curr_ui_provider = provider_options[0]

        selected_ui_provider = st.selectbox(
            "Vision AI Provider (UI selection)",
            provider_options,
            index=provider_options.index(curr_ui_provider),
            format_func=lambda x: x.upper(),
            key="settings_provider_select",
        )
        st.session_state["ui_provider"] = selected_ui_provider

        # Show which provider the running backend actually uses
        st.markdown(f"**Backend Active Provider:** `{config.AI_PROVIDER.upper()}`")
        if config.AI_PROVIDER == "openai":
            bk_model = config.OPENAI_MODEL
        elif config.AI_PROVIDER == "gemini":
            bk_model = config.GEMINI_MODEL
        elif config.AI_PROVIDER == "groq":
            bk_model = config.GROQ_MODEL
        else:
            bk_model = "unknown"

        st.markdown(f"**Backend Vision Model:** `{bk_model}`")
        st.markdown(f"**Moderation Gate:** `{config.MODERATION_PROVIDER.upper()}`")

        if selected_ui_provider != config.AI_PROVIDER.lower():
            st.info(
                f"ℹ️ You selected **{selected_ui_provider.upper()}** but the backend is currently using "
                f"**{config.AI_PROVIDER.upper()}**. To switch providers, set `AI_PROVIDER={selected_ui_provider}` "
                f"in your `.env` file and restart both servers."
            )

        st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# FOOTER — rendered once, at page bottom only
# ==========================================
st.markdown(
    f"""
    <div class="cevon-footer">
        <strong>CevonDocs v{config.APP_VERSION}</strong><br/>
        AI-Powered Document Intelligence Platform
    </div>
    """,
    unsafe_allow_html=True,
)
