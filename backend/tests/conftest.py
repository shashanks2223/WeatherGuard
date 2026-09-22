import pytest
from pathlib import Path
from backend.app.schemas.weather import WeatherSnapshot
from backend.app.schemas.intent import UserIntent, CategoryEnum, UserGroupEnum
from backend.app.services.policy_engine import PolicyEngine
from backend.app.services.weather_service import OpenMeteoClient

@pytest.fixture
def policy_engine():
    policies_dir = Path(__file__).resolve().parent.parent / "app" / "policies"
    return PolicyEngine(policies_dir=policies_dir)

@pytest.fixture
def weather_client():
    return OpenMeteoClient()

@pytest.fixture
def benign_weather():
    return WeatherSnapshot(
        timestamp="2026-09-22T12:00:00Z",
        temperature_c=22.0,
        apparent_temperature_c=22.5,
        wind_speed_kmh=12.0,
        precipitation_mm=0.0,
        precipitation_probability=10,
        uv_index=4.0
    )

@pytest.fixture
def high_wind_weather():
    return WeatherSnapshot(
        timestamp="2026-09-22T12:00:00Z",
        temperature_c=20.0,
        apparent_temperature_c=19.5,
        wind_speed_kmh=44.0,
        precipitation_mm=0.0,
        precipitation_probability=20,
        uv_index=3.0
    )

@pytest.fixture
def storm_weather():
    return WeatherSnapshot(
        timestamp="2026-09-22T12:00:00Z",
        temperature_c=18.0,
        apparent_temperature_c=17.0,
        wind_speed_kmh=52.0,
        precipitation_mm=12.0,
        precipitation_probability=95,
        uv_index=1.0
    )
