from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(..., min_length=1, max_length=200)
    name: str = Field(..., min_length=1, max_length=200)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    admin1: Optional[str] = Field(None, min_length=1, max_length=100)
    timezone: Optional[str] = Field(None, min_length=1, max_length=100)


class WeatherSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    temperature_c: float
    apparent_temperature_c: Optional[float] = None
    wind_speed_kmh: float = Field(..., ge=0.0)
    precipitation_mm: float = Field(0.0, ge=0.0)
    precipitation_probability: Optional[float] = Field(None, ge=0.0, le=100.0)
    uv_index: Optional[float] = Field(None, ge=0.0)
    weather_code: Optional[int] = Field(None, ge=0)
    relative_humidity_2m: Optional[float] = Field(None, ge=0.0, le=100.0)


# Compatibility name used by the pre-existing weather service and graph modules.
LocationResolved = Location
