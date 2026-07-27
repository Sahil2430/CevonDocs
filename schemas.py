from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# Extraction Schema (used with OpenAI response_format)
class LineItem(BaseModel):
    description: str = Field(description="Description of the line item")
    quantity: float = Field(description="Quantity purchased")
    unit_price: float = Field(description="Price per unit")
    amount: float = Field(description="Total line item amount")
    confidence: float = Field(description="Confidence score 0.0 to 1.0 for this line item")


class InvoiceSchema(BaseModel):
    model_config = {"extra": "allow"}

    vendor: str = Field(description="Vendor or merchant name")
    vendor_confidence: float = Field(description="Confidence score 0.0 to 1.0 for vendor")
    invoice_number: str = Field(description="Invoice or receipt reference number")
    invoice_number_confidence: float = Field(description="Confidence score 0.0 to 1.0 for invoice number")
    date: str = Field(description="Invoice date string")
    date_confidence: float = Field(description="Confidence score 0.0 to 1.0 for date")
    currency: str = Field(description="3-letter currency code or symbol")
    currency_confidence: float = Field(description="Confidence score 0.0 to 1.0 for currency")
    subtotal: float = Field(description="Subtotal amount before tax")
    subtotal_confidence: float = Field(description="Confidence score 0.0 to 1.0 for subtotal")
    tax: float = Field(description="Tax amount")
    tax_confidence: float = Field(description="Confidence score 0.0 to 1.0 for tax")
    total: float = Field(description="Total transaction amount")
    total_confidence: float = Field(description="Confidence score 0.0 to 1.0 for total")
    line_items: List[LineItem] = Field(description="List of purchased line items")
    overall_confidence: float = Field(description="Overall document extraction confidence score 0.0 to 1.0")


# API Request/Response Schemas
class IngestResponse(BaseModel):
    document_id: str
    status: str
    extracted_data: Optional[Dict[str, Any]] = None
    flagged_fields: List[str] = Field(default_factory=list)


class ReviewItem(BaseModel):
    document_id: str
    filename: str
    status: str
    extracted_json: Dict[str, Any]
    flagged_fields: List[str]
    created_at: str


class ReviewResponse(BaseModel):
    documents: List[ReviewItem]


class ApproveRequest(BaseModel):
    document_id: str
    reviewed_data: Dict[str, Any]


class ApproveResponse(BaseModel):
    document_id: str
    status: str
    message: str
