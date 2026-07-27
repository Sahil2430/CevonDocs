"""
Rule-Based Confidence Validation Engine for CevonDocs.
Evaluates normalized invoice extraction data against deterministic financial,
numeric, required field, date, and resolution validation rules.
Recalibrated confidence formula prevents inflation and ensures realistic scores.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional

logger = logging.getLogger("cevondocs")


@dataclass
class ValidationResult:
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence_adjustment: float = 0.0
    final_confidence: float = 0.0
    total_checks: int = 0
    score_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warnings": self.warnings,
            "confidence_adjustment": round(self.confidence_adjustment, 3),
            "final_confidence": round(self.final_confidence, 2),
            "total_checks": self.total_checks,
            "score_percent": round(self.score_percent, 1),
        }


def parse_invoice_date(date_str: str) -> Optional[date]:
    """Attempts to parse common invoice date formats into a datetime.date object."""
    if not date_str or not isinstance(date_str, str):
        return None
    
    clean_str = date_str.strip()
    if not clean_str:
        return None

    # Clean brackets or surrounding text if present
    clean_str = re.sub(r"[\[\]]", "", clean_str)

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt).date()
        except ValueError:
            continue
            
    return None


def evaluate_validation(
    extracted_data: Dict[str, Any],
    image_metadata: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """
    Evaluates extracted invoice dictionary against deterministic validation rules.
    Recalibrated Formula (Option A):
        Final Confidence = Clamp(0.85 * AI_Confidence + 0.15 * Validation_Score - Penalties, 0.0, 1.0)
    """
    passed: List[str] = []
    failed: List[str] = []
    warnings: List[str] = []
    penalties: float = 0.0

    data = extracted_data if isinstance(extracted_data, dict) else {}
    base_ai_confidence = float(data.get("overall_confidence", 0.80) or 0.80)

    # ----------------------------------------------------
    # 1. Financial Consistency: Subtotal + Tax ≈ Total (±0.01)
    # ----------------------------------------------------
    subtotal = float(data.get("subtotal") or 0.0)
    tax = float(data.get("tax") or 0.0)
    total = float(data.get("total") or 0.0)

    if total > 0 or subtotal > 0:
        expected_total = subtotal + tax
        if abs(expected_total - total) <= 0.01:
            passed.append("Financial totals verified (Subtotal + Tax = Total)")
        else:
            penalties += 0.15
            failed.append(f"Subtotal + Tax ({subtotal:.2f} + {tax:.2f} = {expected_total:.2f}) does not equal Total ({total:.2f})")
    else:
        warnings.append("Financial totals missing or zero; skipped total verification")

    # ----------------------------------------------------
    # 2. Line Item Consistency: sum(line_item.amount) ≈ subtotal (±0.01)
    # ----------------------------------------------------
    line_items = data.get("line_items", [])
    if isinstance(line_items, list) and len(line_items) > 0:
        line_sum = 0.0
        for item in line_items:
            if isinstance(item, dict):
                line_sum += float(item.get("amount") or 0.0)

        if subtotal > 0:
            if abs(line_sum - subtotal) <= 0.01:
                passed.append("Line item amounts sum matches subtotal")
            else:
                penalties += 0.10
                failed.append(f"Line item amounts sum ({line_sum:.2f}) does not match subtotal ({subtotal:.2f})")
        else:
            passed.append(f"Line items present ({len(line_items)} items)")
    else:
        warnings.append("No line items extracted")

    # ----------------------------------------------------
    # 3. Required Fields Check (-0.05 per missing field penalty)
    # ----------------------------------------------------
    required_fields = {
        "vendor": "Vendor Name",
        "invoice_number": "Invoice Number",
        "date": "Invoice Date",
        "currency": "Currency",
    }

    for req_key, req_label in required_fields.items():
        val = data.get(req_key)
        if not val or not str(val).strip():
            penalties += 0.05
            failed.append(f"Missing required field: {req_label}")
        else:
            passed.append(f"Required field present: {req_label}")

    # Numeric Required Fields (Total & Subtotal)
    if total <= 0.0:
        penalties += 0.05
        failed.append("Missing required field: Total Amount")
    else:
        passed.append("Required field present: Total Amount")

    if subtotal <= 0.0:
        penalties += 0.05
        failed.append("Missing required field: Subtotal Amount")
    else:
        passed.append("Required field present: Subtotal Amount")

    # ----------------------------------------------------
    # 4. Numeric Validation: Reject Negative Values (-0.10 penalty each)
    # ----------------------------------------------------
    numeric_checks = [("subtotal", subtotal), ("tax", tax), ("total", total)]
    for num_name, num_val in numeric_checks:
        if num_val < 0.0:
            penalties += 0.10
            failed.append(f"Negative numeric value rejected: {num_name} ({num_val})")

    if isinstance(line_items, list):
        for idx, item in enumerate(line_items):
            if isinstance(item, dict):
                for item_field in ["quantity", "unit_price", "amount"]:
                    i_val = float(item.get(item_field) or 0.0)
                    if i_val < 0.0:
                        penalties += 0.10
                        failed.append(f"Negative line item value rejected: item[{idx}].{item_field} ({i_val})")

    # ----------------------------------------------------
    # 5. Date Validation: Reject Future Dates (-0.05 penalty)
    # ----------------------------------------------------
    date_val_str = str(data.get("date") or "").strip()
    if date_val_str:
        parsed_dt = parse_invoice_date(date_val_str)
        if parsed_dt:
            if parsed_dt > date.today():
                penalties += 0.05
                failed.append(f"Future invoice date detected ({date_val_str})")
            else:
                passed.append("Invoice date verified (historical / current)")
        else:
            warnings.append(f"Unparseable invoice date format: '{date_val_str}'")

    # ----------------------------------------------------
    # 6. Currency Validation (-0.03 penalty if missing)
    # ----------------------------------------------------
    currency_val = str(data.get("currency") or "").strip()
    if not currency_val or currency_val == "0":
        pass
    else:
        passed.append(f"Currency code verified ({currency_val})")

    # ----------------------------------------------------
    # 7. Duplicate Line Items Check (Warning only, 0 penalty)
    # ----------------------------------------------------
    if isinstance(line_items, list) and len(line_items) > 1:
        seen_items = set()
        has_dupes = False
        for item in line_items:
            if isinstance(item, dict):
                item_key = (
                    str(item.get("description", "")).strip().lower(),
                    float(item.get("quantity") or 0.0),
                    float(item.get("unit_price") or 0.0),
                    float(item.get("amount") or 0.0),
                )
                if item_key in seen_items:
                    has_dupes = True
                    break
                seen_items.add(item_key)
        if has_dupes:
            warnings.append("Duplicate line items detected")

    # ----------------------------------------------------
    # 8. Image Metadata Resolution Check (-0.03 if < 500px)
    # ----------------------------------------------------
    if image_metadata and isinstance(image_metadata, dict):
        width = int(image_metadata.get("width") or 0)
        height = int(image_metadata.get("height") or 0)
        min_dim = min(width, height) if (width > 0 and height > 0) else max(width, height)
        if 0 < min_dim < 500:
            penalties += 0.03
            warnings.append(f"Low resolution image ({width}x{height}px < 500px)")
        elif min_dim >= 500:
            passed.append(f"Image resolution verified ({width}x{height}px)")

    # ----------------------------------------------------
    # Recalibrated Formula Calculation (Weighted Blend: 0.90 * AI + 0.10 * ValScore - Penalties)
    # ----------------------------------------------------
    total_checks = len(passed) + len(failed)
    val_score = (len(passed) / total_checks) if total_checks > 0 else 1.0
    score_pct = val_score * 100.0

    raw_calibrated = (0.90 * base_ai_confidence) + (0.10 * val_score) - penalties
    final_conf = max(0.0, min(1.0, round(raw_calibrated, 2)))
    adjustment = round(final_conf - base_ai_confidence, 3)

    result = ValidationResult(
        passed_checks=passed,
        failed_checks=failed,
        warnings=warnings,
        confidence_adjustment=adjustment,
        final_confidence=final_conf,
        total_checks=total_checks,
        score_percent=round(score_pct, 1),
    )

    log_passed = " ".join([f"✔ {c.split(':')[0]}" for c in passed])
    log_failed = " ".join([f"❌ {c.split(':')[0]}" for c in failed])
    log_warn = " ".join([f"⚠ {w}" for w in warnings])

    logger.info(
        f"Validation Recalibration | AI Base Confidence: {base_ai_confidence:.2f} | "
        f"Validation Score: {val_score:.2f} ({len(passed)}/{total_checks}) | "
        f"Penalties: {penalties:.2f} | Final Calibrated Confidence: {final_conf:.2f} | "
        f"Passed: [{log_passed}] | Failed: [{log_failed}] | Warnings: [{log_warn}]"
    )

    return result
