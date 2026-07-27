import logging
from typing import Union, List, Tuple, Dict, Any
import config
from schemas import InvoiceSchema

logger = logging.getLogger("cevondocs")


def route_document(
    invoice_data: Union[InvoiceSchema, Dict[str, Any]],
    threshold: float = config.REVIEW_THRESHOLD,
) -> Tuple[str, List[str]]:
    """
    Inspects all confidence fields in the invoice data against the threshold.
    Returns (status, flagged_fields).
      - status: 'auto_approved' or 'pending_review'
      - flagged_fields: list of field names below threshold
    """
    if isinstance(invoice_data, InvoiceSchema):
        data = invoice_data.model_dump()
    else:
        data = invoice_data

    flagged_fields: List[str] = []

    # Map of confidence field to readable field name
    top_level_map = {
        "vendor_confidence": "vendor",
        "invoice_number_confidence": "invoice_number",
        "date_confidence": "date",
        "currency_confidence": "currency",
        "subtotal_confidence": "subtotal",
        "tax_confidence": "tax",
        "total_confidence": "total",
    }

    # 0. Check overall confidence (validation-adjusted)
    ov_conf = data.get("overall_confidence")
    is_overall_low = (ov_conf is not None and float(ov_conf) < threshold)

    # 1. Check top-level confidence fields
    for conf_key, field_name in top_level_map.items():
        conf_val = data.get(conf_key)
        if conf_val is None:
            conf_val = 0.0
        if conf_val < threshold:
            flagged_fields.append(field_name)

    # 2. Check line items confidence
    line_items = data.get("line_items", [])
    for idx, item in enumerate(line_items):
        if isinstance(item, dict):
            item_conf = item.get("confidence")
        else:
            item_conf = getattr(item, "confidence", None)
        if item_conf is None:
            item_conf = 0.0
        if item_conf < threshold:
            flagged_fields.append(f"line_items[{idx}]")

    # 3. Determine status
    if flagged_fields or is_overall_low:
        status = "pending_review"
    else:
        status = "auto_approved"

    logger.info(f"Routed document: status='{status}', overall_conf={ov_conf}, flagged_count={len(flagged_fields)}")
    return status, flagged_fields
