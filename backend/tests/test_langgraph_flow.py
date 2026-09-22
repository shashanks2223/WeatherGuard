import pytest
from unittest.mock import AsyncMock
from backend.app.graph.graph import create_weatherguard_graph
from backend.app.graph.nodes import GraphNodes
from backend.app.schemas.decision import DecisionStatus
from backend.app.schemas.weather import LocationResolved, WeatherSnapshot
from backend.app.services.weather_service import OpenMeteoClient, WeatherServiceError

@pytest.mark.asyncio
async def test_missing_location_branch():
    app = create_weatherguard_graph()
    config = {"configurable": {"thread_id": "test-missing-loc"}}
    res = await app.ainvoke({
        "user_query": "Can I cycle today?",
        "session_id": "test-missing-loc",
        "history": []
    }, config=config)

    assert res["decision"].status == DecisionStatus.LOCATION_REQUIRED
    assert "specify the city or location" in res["response_text"].lower()

@pytest.mark.asyncio
async def test_location_failure_branch():
    app = create_weatherguard_graph()
    config = {"configurable": {"thread_id": "test-loc-fail"}}
    res = await app.ainvoke({
        "user_query": "Can I cycle in Xqzjfk1234NotFoundCity today?",
        "session_id": "test-loc-fail",
        "history": []
    }, config=config)

    assert res["decision"].status == DecisionStatus.LOCATION_ERROR
    assert "couldn't resolve the location" in res["response_text"].lower()

@pytest.mark.asyncio
async def test_weather_failure_branch():
    # Mock weather client to raise WeatherServiceError
    mock_weather_client = OpenMeteoClient()
    mock_weather_client.resolve_location = AsyncMock(return_value=LocationResolved(
        query="MockCity",
        name="MockCity",
        latitude=10.0,
        longitude=20.0
    ))
    mock_weather_client.fetch_weather = AsyncMock(side_effect=WeatherServiceError("API down"))

    nodes = GraphNodes(weather_client=mock_weather_client)
    app = create_weatherguard_graph(nodes=nodes)
    config = {"configurable": {"thread_id": "test-wx-fail"}}

    res = await app.ainvoke({
        "user_query": "Can I cycle in MockCity today?",
        "session_id": "test-wx-fail",
        "history": []
    }, config=config)

    assert res["decision"].status == DecisionStatus.WEATHER_ERROR
    assert "couldn't retrieve current weather data" in res["response_text"].lower()

@pytest.mark.asyncio
async def test_multi_turn_session_memory():
    app = create_weatherguard_graph()
    config = {"configurable": {"thread_id": "test-session-flow"}}

    # Turn 1: sets cycling and Bengaluru
    res1 = await app.ainvoke({
        "user_query": "Can I cycle in Bengaluru today?",
        "session_id": "test-session-flow",
        "history": []
    }, config=config)

    assert res1["intent"].location == "Bengaluru"
    assert res1["intent"].activity == "cycling"

    # Turn 2: follow-up without mentioning location or activity
    res2 = await app.ainvoke({
        "user_query": "What about this evening?",
        "session_id": "test-session-flow"
    }, config=config)

    # Must inherit Bengaluru and cycling from session checkpointer!
    assert res2["intent"].location == "Bengaluru"
    assert res2["intent"].activity == "cycling"
    assert "evening" in res2["intent"].time_scope.lower()
