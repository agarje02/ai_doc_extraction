"""Built-in Invoice / receipt schema."""
from __future__ import annotations

from .base import DocSchema, FieldSpec

INVOICE_SCHEMA = DocSchema(
    key="invoice",
    name="Invoice / Receipt",
    description="Financial document with vendor, buyer, line items and totals.",
    fields=[
        FieldSpec(name="invoice_number", type="string", required=True,
                  description="The unique invoice or receipt number/id.",
                  example="INV-2024-0091"),
        FieldSpec(name="invoice_date", type="date",
                  description="Date the invoice was issued."),
        FieldSpec(name="due_date", type="date",
                  description="Date payment is due."),
        FieldSpec(name="vendor_name", type="string",
                  description="Name of the seller / vendor / merchant."),
        FieldSpec(name="vendor_tax_id", type="string",
                  description="Vendor tax / VAT / GST identifier."),
        FieldSpec(name="bill_to_name", type="string",
                  description="Name of the customer being billed."),
        FieldSpec(name="currency", type="string",
                  description="ISO currency code, e.g. USD, EUR, INR."),
        FieldSpec(name="subtotal", type="currency",
                  description="Amount before tax."),
        FieldSpec(name="tax_amount", type="currency",
                  description="Total tax charged."),
        FieldSpec(name="total_amount", type="currency", required=True,
                  description="Grand total payable."),
        FieldSpec(name="line_items", type="text", many=True,
                  description="Each line item as 'description x qty @ unit_price = amount'."),
    ],
)
