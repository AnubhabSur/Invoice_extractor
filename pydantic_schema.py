"""
pydantic_schema.py
==================
Defines the Pydantic models for invoice data extraction.
Imported by invoice_extractor.py — do not run this file directly.

NOTE: Gemini's response_schema does NOT support default values.
      All fields must use Optional[str] with NO default (= None or = []).
      Gemini returns null for missing fields — Pydantic accepts that fine.

Install:
    pip install pydantic
"""

from typing import Optional
from pydantic import BaseModel


# ── Line item row ─────────────────────────────────────────────────────────────
class LineItem(BaseModel):
    """A single line item row on the invoice."""
    description: Optional[str]   # ← no = None
    quantity:    Optional[str]
    unit_price:  Optional[str]
    amount:      Optional[str]


# ── Full invoice ──────────────────────────────────────────────────────────────
class Invoice(BaseModel):
    """
    Full invoice structure.
    Gemini will strictly follow this schema at the API level
    when passed as response_schema in GenerationConfig.
    """

    # Header
    invoice_number:  Optional[str]
    invoice_date:    Optional[str]
    due_date:        Optional[str]

    # Vendor details
    vendor_name:     Optional[str]
    vendor_address:  Optional[str]
    vendor_email:    Optional[str]
    vendor_phone:    Optional[str]

    # Bill-to details
    bill_to_name:    Optional[str]
    bill_to_address: Optional[str]
    bill_to_email:   Optional[str]

    # Financials
    subtotal:        Optional[str]
    tax:             Optional[str]
    discount:        Optional[str]
    total_amount:    Optional[str]
    currency:        Optional[str]

    # Payment info
    payment_terms:   Optional[str]
    payment_method:  Optional[str]
    notes:           Optional[str]

    # Line items — no default [] allowed, Gemini handles the list natively
    line_items:      list[LineItem]