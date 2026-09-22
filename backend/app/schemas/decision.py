from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.intent import Intent
from backend.app.schemas.policy import Policy, PolicyMatch, SeverityLevel
from backend.app.schemas.weather import Location, WeatherSnapshot


class DecisionStatus(str, Enum):
    MATCHED = "MATCHED"
    NO_POLICY = "NO_POLICY"
    LOCATION_REQUIRED = "LOCATION_REQUIRED"
    LOCATION_ERROR = "LOCATION_ERROR"
    WEATHER_ERROR = "WEATHER_ERROR"


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: DecisionStatus
    selected_policy_id: Optional[str] = Field(None, min_length=1)
    selected_policy: Optional[Policy] = None
    severity: Optional[SeverityLevel] = None
    matched_policies: List[PolicyMatch] = Field(default_factory=list)
    matched_policy_ids: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    selection_reason: Optional[str] = None


class EvidencePack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    location: Optional[Location] = None
    weather: Optional[WeatherSnapshot] = None
    matched_policies: List[PolicyMatch] = Field(default_factory=list)
    selected_policy: Optional[Policy] = None
    severity: Optional[SeverityLevel] = None
    matched_conditions: List[str] = Field(default_factory=list)
    evidence_fields: List[str] = Field(default_factory=list)
    selection_reason: Optional[str] = None
    timestamp: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    session_id: Optional[str] = Field(None, min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., min_length=1, max_length=200)
    response: str = Field(..., min_length=1)
    decision: PolicyDecision
    evidence: Optional[EvidencePack] = None
    validation_passed: bool = True


# Compatibility name used by the pre-existing graph and API modules.
Decision = PolicyDecision
