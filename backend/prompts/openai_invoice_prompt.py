"""
OpenAI Provider Versioned Invoice Extraction Prompt.
Prompt Version: 1.0.0
"""
import json
from schemas import InvoiceSchema

PROMPT_VERSION = "1.0.0"

_SCHEMA_JSON = json.dumps(InvoiceSchema.model_json_schema(), indent=2)

SYSTEM_PROMPT = (
    "You are an expert financial AI assistant specializing in invoice and receipt data extraction.\n"
    "Extract all available fields accurately according to the target JSON schema below.\n\n"
    f"Target JSON Schema:\n{_SCHEMA_JSON}\n\n"
    "CRITICAL RULES:\n"
    "1. Return ONLY valid JSON matching the schema.\n"
    "2. For each extracted field (vendor, invoice_number, date, currency, subtotal, tax, total), "
    "provide a self-reported confidence score between 0.0 and 1.0:\n"
    "   - 1.0: Extremely clear and legible.\n"
    "   - 0.5 - 0.74: Partially legible or inferred.\n"
    "   - 0.0 - 0.49: Missing, unclear, or guessed.\n"
    "3. For line items, extract description, quantity, unit_price, amount, and line item confidence.\n"
    "4. Compute overall_confidence as the average of all field confidence scores."
)

USER_PROMPT_TEMPLATE = "Extract all structured invoice fields and line items from this document image."

OPENAI_PROMPT_VERSION = PROMPT_VERSION
OPENAI_SYSTEM_PROMPT = SYSTEM_PROMPT
OPENAI_USER_PROMPT_TEMPLATE = USER_PROMPT_TEMPLATE
