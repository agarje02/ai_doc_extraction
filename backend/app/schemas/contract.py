"""Built-in Contract / legal agreement schema."""
from __future__ import annotations

from .base import DocSchema, FieldSpec

CONTRACT_SCHEMA = DocSchema(
    key="contract",
    name="Contract / Agreement",
    description="Legal agreement with parties, dates, term and financial terms.",
    fields=[
        FieldSpec(name="title", type="string",
                  description="Title / type of the agreement."),
        FieldSpec(name="party_a", type="string", required=True,
                  description="First contracting party (e.g. disclosing party)."),
        FieldSpec(name="party_b", type="string", required=True,
                  description="Second contracting party (e.g. receiving party)."),
        FieldSpec(name="effective_date", type="date",
                  description="Date the contract takes effect."),
        FieldSpec(name="expiration_date", type="date",
                  description="Date the contract expires, if any."),
        FieldSpec(name="term", type="string",
                  description="Duration / term of the agreement."),
        FieldSpec(name="governing_law", type="string",
                  description="Jurisdiction / governing law clause."),
        FieldSpec(name="contract_value", type="currency",
                  description="Total monetary value if stated."),
        FieldSpec(name="currency", type="string",
                  description="Currency of the contract value."),
        FieldSpec(name="termination_notice", type="string",
                  description="Notice period required for termination."),
        FieldSpec(name="obligations", type="text", many=True,
                  description="Key obligations or deliverables per party."),
    ],
)
