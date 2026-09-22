import pytest
from unittest.mock import AsyncMock, patch
import httpx

from backend.app.services.weather_service import (
    GeocodingError,
    OpenMeteoClient,
    WeatherServiceError,
)

@pytest.mark.asyncio
async def test_resolve_location_success(weather_client: OpenMeteoClient):
    loc = await weather_client.resolve_location("London")
    assert loc is not None
    assert "London" in loc.name
    assert isinstance(loc.latitude, float)
    assert isinstance(loc.longitude, float)

@pytest.mark.asyncio
async def test_resolve_location_unknown(weather_client: OpenMeteoClient):
    # Nonexistent gibberish city
    loc = await weather_client.resolve_location("Xqzjfk1234NotFoundCity")
    assert loc is None

@pytest.mark.asyncio
async def test_fetch_weather_success(weather_client: OpenMeteoClient):
    # Fetch for Bengaluru coordinates
    snapshot = await weather_client.fetch_weather(12.9719, 77.5937)
    assert snapshot is not None
    assert isinstance(snapshot.temperature_c, float)
    assert isinstance(snapshot.wind_speed_kmh, float)
    assert isinstance(snapshot.precipitation_mm, float)

@pytest.mark.asyncio
async def test_fetch_weather_network_failure():
    client = OpenMeteoClient()
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network unreachable")):
        with pytest.raises(WeatherServiceError):
            await client.fetch_weather(0.0, 0.0)

@pytest.mark.asyncio
async def test_geocoding_network_failure():
    client = OpenMeteoClient()
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network unreachable")):
        with pytest.raises(GeocodingError):
            await client.resolve_location("Paris")
