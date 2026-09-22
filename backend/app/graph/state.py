from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from backend.app.schemas.decision import Decision, EvidencePack
from backend.app.schemas.intent import UserIntent
from backend.app.schemas.policy import PolicyMatch
from backend.app.schemas.weather import LocationResolved, WeatherSnapshot

class WeatherGuardState(TypedDict):
    # Session & Conversation Tracking
    session_id: str
    user_query: str
    history: List[Dict[str, str]]

    # Pipeline Extracted Data
    intent: Optional[UserIntent]
    location_query: Optional[str]
    location: Optional[LocationResolved]
    weather: Optional[WeatherSnapshot]

    # Policy Decisions
    matched_policies: List[PolicyMatch]
    selected_policy: Optional[PolicyMatch]
    decision: Optional[Decision]
    evidence_pack: Optional[EvidencePack]

    # Output & Auditing
    response_text: Optional[str]
    error_message: Optional[str]
    validation_passed: bool
