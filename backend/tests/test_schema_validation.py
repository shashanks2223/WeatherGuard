from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.app.schemas.decision import ChatRequest, ChatResponse, EvidencePack, PolicyDecision
from backend.app.schemas.intent import CategoryEnum, Intent, UserGroupEnum
from backend.app.schemas.policy import Policy, PolicyConditions, SeverityLevel
from backend.app.schemas.weather import Location, WeatherSnapshot


@pytest.fixture
def valid_policy_data() -> dict:
    return {
        "id": "EXAMPLE-01",
        "name": "Example policy",
        "category": "outdoor_exercise",
        "applies_to": {"activities": ["cycling"]},
        "conditions": {
            "all": [
                {"field": "wind_speed_kmh", "operator": ">=", "value": 35}
            ]
        },
        "severity": "high",
        "guidance": {
            "title": "High wind",
            "recommendation": "Avoid cycling in these conditions.",
        },
    }


def test_intent_and_weather_validate_external_values() -> None:
    intent = Intent(
        activity="cycling",
        category=CategoryEnum.OUTDOOR_EXERCISE,
        location="Bengaluru",
        user_group=UserGroupEnum.ADULT,
        confidence=0.8,
    )
    weather = WeatherSnapshot(
        timestamp="2026-09-22T12:00:00Z",
        temperature_c=24,
        wind_speed_kmh=12,
        precipitation_probability=25,
    )

    assert intent.activity == "cycling"
    assert weather.timestamp.tzinfo == timezone.utc


def test_location_rejects_invalid_coordinates() -> None:
    with pytest.raises(ValidationError):
        Location(query="Somewhere", name="Somewhere", latitude=91, longitude=0)


def test_policy_conditions_are_typed_and_generic(valid_policy_data: dict) -> None:
    policy = Policy.model_validate(valid_policy_data)

    assert isinstance(policy.conditions, PolicyConditions)
    assert policy.conditions.all is not None
    assert policy.conditions.all[0].field == "wind_speed_kmh"
    assert policy.severity is SeverityLevel.HIGH


def test_policy_rejects_unknown_external_fields(valid_policy_data: dict) -> None:
    invalid_policy = {**valid_policy_data, "unexpected": True}

    with pytest.raises(ValidationError):
        Policy.model_validate(invalid_policy)


def test_policy_requires_a_condition_block(valid_policy_data: dict) -> None:
    invalid_policy = {**valid_policy_data, "conditions": {}}

    with pytest.raises(ValidationError):
        Policy.model_validate(invalid_policy)


def test_evidence_and_chat_models_are_composed_from_typed_models() -> None:
    intent = Intent(activity="walking")
    weather = WeatherSnapshot(
        timestamp=datetime.now(timezone.utc),
        temperature_c=20,
        wind_speed_kmh=8,
    )
    evidence = EvidencePack(
        intent=intent,
        weather=weather,
        timestamp="2026-09-22T12:00:00Z",
    )
    response = ChatResponse(
        session_id="session-1",
        response="No policy-backed decision yet.",
        decision=PolicyDecision(status="NO_POLICY"),
        evidence=evidence,
    )

    assert response.evidence is evidence
    assert response.decision.status.value == "NO_POLICY"


def test_chat_request_rejects_blank_or_unknown_input() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")

    with pytest.raises(ValidationError):
        ChatRequest(message="Can I walk?", extra_field="not allowed")
