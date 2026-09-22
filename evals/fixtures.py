from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock

from backend.app.graph.graph import create_weatherguard_graph
from backend.app.graph.nodes import GraphNodes
from backend.app.schemas.intent import CategoryEnum, UserGroupEnum, UserIntent
from backend.app.schemas.weather import LocationResolved, WeatherSnapshot
from backend.app.services.policy_engine import PolicyEngine
from backend.app.services.weather_service import OpenMeteoClient

ROOT = Path(__file__).resolve().parent.parent
POLICIES_DIR = ROOT / "backend" / "app" / "policies"


def normal_weather() -> WeatherSnapshot:
    return WeatherSnapshot(
        timestamp=datetime(2026, 9, 22, 12, tzinfo=timezone.utc),
        temperature_c=24.0,
        wind_speed_kmh=16.0,
        precipitation_mm=0.0,
        precipitation_probability=8.0,
        uv_index=4.5,
    )


def location(name: str = "EvalCity") -> LocationResolved:
    return LocationResolved(
        query=name,
        name=name,
        latitude=12.9716,
        longitude=77.5946,
        country="India",
        timezone="Asia/Kolkata",
    )


def policy_engine() -> PolicyEngine:
    return PolicyEngine(policies_dir=POLICIES_DIR)


def find_policy(engine: PolicyEngine, predicate: Callable[[Any], bool]):
    for policy in engine.policies:
        if predicate(policy):
            return policy
    raise AssertionError("No policy in the loaded registry matched the evaluator predicate")


def threshold(policy: Any, field: str, operator: Optional[str] = None) -> Any:
    blocks = policy.conditions.model_dump(exclude_none=True)
    conditions = blocks.get("all", []) + blocks.get("any", [])
    profile = blocks.get("composite_profile")
    if profile:
        conditions += profile.get("rules", [])
    for condition in conditions:
        if condition["field"] == field and (operator is None or condition["operator"] == operator):
            return condition
    raise AssertionError(f"No condition for {field!r} found in {policy.id}")


def weather_for_condition(policy: Any, field: str, margin: float = 1.0) -> WeatherSnapshot:
    weather = normal_weather().model_dump()
    condition = threshold(policy, field)
    operator = condition["operator"]
    value = condition["value"]
    if not isinstance(value, (int, float)):
        raise AssertionError(f"Evaluator requires numeric condition for {policy.id}:{field}")
    if operator in (">=", ">"):
        actual = value + margin
    elif operator in ("<=", "<"):
        actual = value - margin
    elif operator == "==":
        actual = value
    else:
        raise AssertionError(f"Unsupported boundary construction operator: {operator}")
    weather[field] = actual
    return WeatherSnapshot.model_validate(weather)


def graph_with_weather(weather: WeatherSnapshot, location_name: str = "EvalCity"):
    client = OpenMeteoClient()
    client.resolve_location = AsyncMock(return_value=location(location_name))
    client.fetch_weather = AsyncMock(return_value=weather)
    return create_weatherguard_graph(GraphNodes(weather_client=client)), client


def graph_with_location_failure():
    client = OpenMeteoClient()
    client.resolve_location = AsyncMock(return_value=None)
    client.fetch_weather = AsyncMock()
    return create_weatherguard_graph(GraphNodes(weather_client=client)), client


def graph_with_weather_failure(error: Exception):
    client = OpenMeteoClient()
    client.resolve_location = AsyncMock(return_value=location())
    client.fetch_weather = AsyncMock(side_effect=error)
    return create_weatherguard_graph(GraphNodes(weather_client=client)), client


def adult_intent(activity: str = "cycling") -> UserIntent:
    return UserIntent(
        activity=activity,
        category=CategoryEnum.OUTDOOR_EXERCISE,
        user_group=UserGroupEnum.ADULT,
    )
