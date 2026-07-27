"""
Groq Provider Versioned Invoice Extraction Prompt.
Prompt Version: 1.0.0
"""
import json
from schemas import InvoiceSchema

PROMPT_VERSION = "1.0.0"

_SCHEMA_JSON = json.dumps(InvoiceSchema.model_json_schema(), indent=2)

SYSTEM_PROMPT = (
    "You are a document intelligence vision AI specialized in extracting receipt and invoice data.\n"
    "Extract all available fields accurately according to the provided target JSON schema.\n\n"
    f"Target JSON Schema:\n{_SCHEMA_JSON}\n\n"
    "CRITICAL INSTRUCTIONS:\n"
    "1. Return ONLY valid JSON. Do NOT output markdown, code fences (e.g. ```json), or explanatory text.\n"
    "2. Every required field in the JSON schema MUST exist in the JSON response.\n"
    "3. Confidence fields (vendor_confidence, invoice_number_confidence, date_confidence, currency_confidence, "
    "subtotal_confidence, tax_confidence, total_confidence, overall_confidence, and line_item confidence) "
    "MUST be floats between 0.0 and 1.0.\n"
    "4. For each line item in line_items, include: description, quantity, unit_price, amount, and confidence.\n"
    "5. If a value cannot be determined, return null (or schema default), but NEVER omit any required schema fields."
)

USER_PROMPT_TEMPLATE = "Extract all structured fields and line items from this receipt/invoice image matching the schema."

GROQ_PROMPT_VERSION = PROMPT_VERSION
GROQ_SYSTEM_PROMPT = SYSTEM_PROMPT
GROQ_USER_PROMPT_TEMPLATE = USER_PROMPT_TEMPLATE
