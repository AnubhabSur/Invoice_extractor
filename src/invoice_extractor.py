"""
Invoice Extractor — Gemini 2.5 Flash
======================================
Extracts structured fields from an invoice image (.jpg / .png / .webp)
and saves the result as a clean JSON file.

Schema is defined separately in pydantic_schema.py and imported here.
Gemini enforces the structure at the API level — no JSON in the prompt.

Requirements:
    pip install google-genai Pillow python-dotenv pydantic

Setup:
    Create a .env file in the project root:
        GEMINI_API_KEY=your_actual_key_here

Usage:
    python invoice_extractor.py --image invoices/invoice_001.jpg
    python invoice_extractor.py --image invoices/invoice_001.jpg --output outputs/result.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ── Auto-load .env ────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("WARNING: 'python-dotenv' not installed. .env file will not be loaded.")
    print("Run:  pip install python-dotenv")

# ── Dependency checks ─────────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: 'google-genai' not installed.")
    print("Run:  pip install google-genai")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("ERROR: 'Pillow' not installed.")
    print("Run:  pip install Pillow")
    sys.exit(1)

try:
    from pydantic import BaseModel
except ImportError:
    print("ERROR: 'pydantic' not installed.")
    print("Run:  pip install pydantic")
    sys.exit(1)

# ── Import Pydantic schema from pydantic_schema.py ───────────────────────────
try:
    from pydantic_schema import Invoice, LineItem
except ImportError:
    print("ERROR: 'pydantic_schema.py' not found.")
    print("Make sure pydantic_schema.py is in the same folder as invoice_extractor.py")
    sys.exit(1)


# ── Prompt ────────────────────────────────────────────────────────────────────
# Simple instruction only — no JSON structure needed here anymore.
# The structure is fully handled by the Pydantic schema in pydantic_schema.py.
EXTRACTION_PROMPT = """
You are an invoice data extraction engine.
Carefully analyze this invoice image and extract every field you can find.
Leave a field as null if it is not present in the invoice.
""".strip()


# ── Field labels for pretty printing ─────────────────────────────────────────
FIELD_LABELS = {
    "invoice_number":  "Invoice Number",
    "invoice_date":    "Invoice Date",
    "due_date":        "Due Date",
    "vendor_name":     "Vendor Name",
    "vendor_address":  "Vendor Address",
    "vendor_email":    "Vendor Email",
    "vendor_phone":    "Vendor Phone",
    "bill_to_name":    "Bill To (Name)",
    "bill_to_address": "Bill To (Address)",
    "bill_to_email":   "Bill To (Email)",
    "subtotal":        "Subtotal",
    "tax":             "Tax",
    "discount":        "Discount",
    "total_amount":    "Total Amount",
    "currency":        "Currency",
    "payment_terms":   "Payment Terms",
    "payment_method":  "Payment Method",
    "notes":           "Notes",
}


# ── Core extraction function ──────────────────────────────────────────────────
def extract_invoice(image_path: str, api_key: str) -> Invoice:
    """
    Send an invoice image to Gemini and return a validated Invoice Pydantic object.

    Args:
        image_path: Path to the invoice image (.jpg / .png / .webp).
        api_key:    Your Gemini API key.

    Returns:
        A fully validated Invoice instance (defined in pydantic_schema.py).
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    print(f"[1/3] Loading image: {path.name}")
    image = Image.open(path)

    print("[2/3] Calling Gemini 2.5 Flash ...")

    # ── New SDK: instantiate a Client (replaces genai.configure + GenerativeModel)
    client = genai.Client(api_key=api_key)

    # ── Schema is passed via response_json_schema using Pydantic's model_json_schema()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[EXTRACTION_PROMPT, image],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",          # force JSON output
            response_json_schema=Invoice.model_json_schema(), # schema from pydantic_schema.py
        ),
    )

    print("[3/3] Validating response with Pydantic ...")
    invoice = Invoice.model_validate_json(response.text)   # parse + validate in one step

    return invoice


# ── Pretty print to console ───────────────────────────────────────────────────
def print_result(invoice: Invoice) -> None:
    """Print the validated Invoice model in a readable table format."""
    print("\n" + "=" * 55)
    print("  EXTRACTED INVOICE FIELDS")
    print("=" * 55)

    for key, label in FIELD_LABELS.items():
        value   = getattr(invoice, key, None)
        display = value if value else "(not found)"
        print(f"  {label:<22} {display}")

    print("\n" + "-" * 55)
    print("  LINE ITEMS")
    print("-" * 55)

    if invoice.line_items:
        print(f"  {'Description':<28} {'Qty':>5}  {'Unit Price':>10}  {'Amount':>10}")
        print("  " + "-" * 51)
        for item in invoice.line_items:
            desc       = (item.description or "—")[:27]
            qty        = item.quantity   or "—"
            unit_price = item.unit_price or "—"
            amount     = item.amount     or "—"
            print(f"  {desc:<28} {qty:>5}  {unit_price:>10}  {amount:>10}")
    else:
        print("  (no line items found)")

    print("=" * 55 + "\n")


# ── Save JSON output ──────────────────────────────────────────────────────────
def save_json(invoice: Invoice, output_path) -> None:
    """Serialize the Pydantic Invoice model to a pretty JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        # model_dump() converts the Pydantic model → plain dict for saving
        json.dump(invoice.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"JSON saved to: {output_path}")


# ── CLI entry point ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Extract invoice fields using Gemini 2.5 Flash + Pydantic schema."
    )
    parser.add_argument("--image",   "-i", required=True, help="Path to invoice image (.jpg, .png, .webp)")
    parser.add_argument("--output",  "-o", default=None,  help="Output JSON path (default: outputs/<n>_extracted.json)")
    parser.add_argument("--api-key", "-k", default=None,  help="Gemini API key (or set GEMINI_API_KEY in .env)")
    args = parser.parse_args()

    # Resolve API key: CLI flag > .env file
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: No API key provided.")
        print("  Option 1: python invoice_extractor.py --api-key YOUR_KEY ...")
        print("  Option 2: Set GEMINI_API_KEY=your_key in your .env file")
        sys.exit(1)

    # Resolve output path — defaults to outputs/<image_stem>_extracted.json
    if args.output:
        output_path = args.output
    else:
        stem       = Path(args.image).stem
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{stem}_extracted.json"

    # Run extraction
    try:
        invoice = extract_invoice(image_path=args.image, api_key=api_key)
        print_result(invoice)
        save_json(invoice, output_path)

    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()