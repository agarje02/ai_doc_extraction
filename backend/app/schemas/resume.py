"""Built-in Resume / CV schema."""
from __future__ import annotations

from .base import DocSchema, FieldSpec

RESUME_SCHEMA = DocSchema(
    key="resume",
    name="Resume / CV",
    description="Candidate profile with contact details, skills and experience.",
    fields=[
        FieldSpec(name="full_name", type="string", required=True,
                  description="Candidate's full name."),
        FieldSpec(name="email", type="email",
                  description="Primary email address."),
        FieldSpec(name="phone", type="phone",
                  description="Primary phone number."),
        FieldSpec(name="location", type="string",
                  description="City / country of residence."),
        FieldSpec(name="current_title", type="string",
                  description="Most recent or current job title."),
        FieldSpec(name="years_experience", type="number",
                  description="Total years of professional experience."),
        FieldSpec(name="skills", type="string", many=True,
                  description="List of technical and professional skills."),
        FieldSpec(name="education", type="text", many=True,
                  description="Each education entry: degree, institution, year."),
        FieldSpec(name="experience", type="text", many=True,
                  description="Each role: title, company, dates, summary."),
        FieldSpec(name="linkedin", type="string",
                  description="LinkedIn profile URL if present."),
    ],
)
