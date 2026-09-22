import pytest
from unittest.mock import AsyncMock

from backend.app.graph.graph import create_weatherguard_graph
from backend.app.graph.nodes import GraphNodes
from backend.app.schemas.decision import DecisionStatus
from backend.app.schemas.weather import LocationResolved, WeatherSnapshot
from backend.app.services.llm_service import MockLLMProvider
from backend.app.services.weather_service import OpenMeteoClient, WeatherServiceError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "Can I cycle today in Bengaluru?",
        "Is biking okay today in Bengaluru?",
        "Can I ride my bicycle this afternoon in Bengaluru?",
        "Would it be alright to pedal to work today in Bengaluru?",
        "Can I bike to college today in Bengaluru?",
    ],
)
async def test_cycling_paraphrases_normalize_to_same_intent(query: str) -> None:
    intent = await MockLLMProvider().extract_intent(query)
    assert intent.activity == "cycling"
    assert intent.category.value == "outdoor_exercise"
    assert intent.user_group.value == "adult"


@pytest.mark.asyncio
async def test_bengaluru_cycle_request_selects_routine_policy_with_live_shape() -> None:
    client = OpenMeteoClient()
    client.resolve_location = AsyncMock(
        return_value=LocationResolved(
            query="Bengaluru",
            name="Bengaluru",
            latitude=12.9716,
            longitude=77.5946,
            country="India",
        )
    )
    client.fetch_weather = AsyncMock(
        return_value=WeatherSnapshot(
            timestamp="2026-09-22T12:00:00Z",
            temperature_c=24.3,
            wind_speed_kmh=18.2,
            precipitation_mm=0.1,
            precipitation_probability=8,
            uv_index=4.9,
        )
    )

    app = create_weatherguard_graph(GraphNodes(weather_client=client))
    result = await app.ainvoke(
        {"user_query": "Can I cycle today in Bengaluru?", "session_id": "cycle-regression"},
        config={"configurable": {"thread_id": "cycle-regression"}},
    )

    assert result["intent"].activity == "cycling"
    assert result["location"].name == "Bengaluru"
    assert result["weather"].wind_speed_kmh == 18.2
    assert result["decision"].status == DecisionStatus.MATCHED
    assert result["decision"].selected_policy_id == "EX-CYCLE-ROUTINE-01"
    assert result["evidence_pack"].selected_policy.id == "EX-CYCLE-ROUTINE-01"
    assert "18.2" in result["response_text"]
    assert "8.0%" in result["response_text"] or "8.0" in result["response_text"]
    assert "4.9" in result["response_text"]


@pytest.mark.asyncio
async def test_weather_failure_has_no_weather_evidence_or_advice() -> None:
    client = OpenMeteoClient()
    client.resolve_location = AsyncMock(
        return_value=LocationResolved(query="Bengaluru", name="Bengaluru", latitude=12.9, longitude=77.5)
    )
    client.fetch_weather = AsyncMock(side_effect=WeatherServiceError("temporary outage"))

    app = create_weatherguard_graph(GraphNodes(weather_client=client))
    result = await app.ainvoke(
        {"user_query": "Can I cycle today in Bengaluru?", "session_id": "weather-failure"},
        config={"configurable": {"thread_id": "weather-failure"}},
    )

    assert result["decision"].status == DecisionStatus.WEATHER_ERROR
    assert result["weather"] is None
    assert result["evidence_pack"].weather is None
    assert "couldn't retrieve current weather data" in result["response_text"].lower()
