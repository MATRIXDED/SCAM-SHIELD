"""
schemas.py — ScamShield Data Validation Models
================================================
Validated schemas for incoming assessment requests and outbound responses.
Guarantees clean bounds checking, size limits, and sanitization.
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class ScamAnalyzeRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The raw untrusted suspicious text to evaluate. Maximum 10,000 characters.",
    )
    channel: Optional[Literal["sms", "email", "payment_app", "social_media", "other"]] = Field(
        default="sms",
        description="Communication channel where the message was received.",
    )
    save_history: Optional[bool] = Field(
        default=False,
        description="Whether the user opts in to logging anonymized scan telemetry (never raw text).",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Message content cannot be blank or whitespace only.")
        return trimmed


class LinkDetail(BaseModel):
    url: str
    domain: str
    is_suspicious: bool
    flags: List[str]


class AnalysisBreakdown(BaseModel):
    urgency: List[str]
    impersonation: List[str]
    suspicious_links: List[str]
    otp_requests: List[str]
    payment_pressure: List[str]
    lures: List[str]


class ScamAnalyzeResponse(BaseModel):
    status: str
    fingerprint: str
    preview_length: int
    risk_score: int
    risk_level: str
    risk_color: str
    summary: str
    warning_signs: List[str]
    breakdown: AnalysisBreakdown
    safe_next_steps: List[str]
    suggested_response: str
    disclaimer: str
    prompt_injection_detected: bool
    links_found: int
    # New fields (v2): method transparency and timestamp
    analysis_method: Optional[str] = None
    analyzed_at: Optional[str] = None


class HistoryItem(BaseModel):
    id: str
    fingerprint: str
    preview_length: int
    risk_score: int
    risk_level: str
    channel: str
    warning_count: int
    created_at: str


class SafeNextStepsResponse(BaseModel):
    emergency_guidance: List[str]
    general_checklist: List[str]
    reporting_resources: Dict[str, str]
