from typing import List, Literal
from pydantic import BaseModel, Field


class Finding(BaseModel):
    id: int = Field(description="Sequential finding number")

    clause: str = Field(
        description="The relevant clause or short quote from the document"
    )

    requirement: str = Field(
        description="The compliance requirement that applies"
    )

    status: Literal["compliant", "non_compliant", "needs_review"] = Field(
        description="Compliance status"
    )

    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Risk severity"
    )

    category: str = Field(
        description="Compliance category such as Privacy, Retention, Security, Sharing"
    )

    risk_reason: str = Field(
        description="Why this clause creates or may create compliance exposure"
    )

    compliant_rewrite: str = Field(
        description="Suggested compliant alternative wording"
    )

    citation: str = Field(
        description="Document location such as Page 3 or Section 5.2"
    )


class ComplianceReport(BaseModel):
    document_name: str

    framework: str

    executive_summary: str

    overall_status: Literal[
        "COMPLIANT",
        "PARTIALLY_COMPLIANT",
        "NON_COMPLIANT",
        "NEEDS_REVIEW"
    ]

    compliance_score: int = Field(
        ge=0,
        le=100,
        description="Estimated compliance score from 0 to 100"
    )

    total_findings: int

    high_risk_count: int

    critical_count: int

    findings: List[Finding]