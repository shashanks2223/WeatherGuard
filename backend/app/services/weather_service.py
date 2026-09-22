import logging
from datetime import datetime
from typing import Any, Dict, Optional
import httpx

from backend.app.schemas.weather import LocationResolved, WeatherSnapshot

logger = logging.getLogger(__name__)

class GeocodingError(Exception):
    """Raised when location lookup fails or is unavailable."""
    pass

class WeatherServiceError(Exception):
    """Raised when Open-Meteo weather forecast retrieval fails."""
    pass

class OpenMeteoClient:
    """Client for Open-Meteo Geocoding and Weather Forecast APIs.

    Strictly queries explicit weather fields and normalizes responses into trusted models.
    """

    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    async def resolve_location(self, query: str) -> Optional[LocationResolved]:
        """Resolves a geographic query string to geographic coordinates using Open-Meteo Geocoding API.

        Returns LocationResolved on success, or None if no location is found.
        Raises GeocodingError on network or API error.
        """
        clean_query = query.strip()
        if not clean_query:
            return None

        params = {
            "name": clean_query,
            "count": 1,
            "language": "en",
            "format": "json"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.GEOCODING_URL, params=params)
                if response.status_code != 200:
                    logger.error(f"Geocoding API returned status code {response.status_code}")
                    raise GeocodingError(f"Geocoding service returned status code {response.status_code}")

                data = response.json()
                results = data.get("results")
                if not results or len(results) == 0:
                    logger.info(f"No geocoding results found for query: '{clean_query}'")
                    return None

                top = results[0]
                return LocationResolved(
                    query=clean_query,
                    name=top.get("name", clean_query),
                    latitude=float(top["latitude"]),
                    longitude=float(top["longitude"]),
                    country=top.get("country"),
                    admin1=top.get("admin1"),
                    timezone=top.get("timezone", "UTC")
                )
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.error(f"Network failure while reaching Open-Meteo geocoding: {exc}")
            raise GeocodingError(f"Unable to reach geocoding service: {str(exc)}") from exc
        except Exception as exc:
            if isinstance(exc, GeocodingError):
                raise
            logger.error(f"Unexpected error resolving location: {exc}")
            raise GeocodingError(f"Unexpected geocoding failure: {str(exc)}") from exc

    async def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        time_scope: str = "current"
    ) -> WeatherSnapshot:
        """Fetches live weather from Open-Meteo with explicit parameter specification.

        Normalizes raw Open-Meteo data into a trusted WeatherSnapshot model.
        Raises WeatherServiceError on network or API failure.
        """
        # Explicitly request required fields
        current_fields = [
            "temperature_2m",
            "apparent_temperature",
            "wind_speed_10m",
            "precipitation",
            "weather_code",
            "relative_humidity_2m"
        ]
        hourly_fields = [
            "temperature_2m",
            "apparent_temperature",
            "wind_speed_10m",
            "precipitation",
            "precipitation_probability",
            "uv_index"
        ]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(current_fields),
            "hourly": ",".join(hourly_fields),
            "forecast_days": 2,
            "timezone": "auto"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.FORECAST_URL, params=params)
                if response.status_code != 200:
                    logger.error(f"Open-Meteo forecast API returned status code {response.status_code}")
                    raise WeatherServiceError(f"Forecast API returned status {response.status_code}")

                data = response.json()
                return self._normalize_weather(data, time_scope)
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.error(f"Network error calling Open-Meteo forecast API: {exc}")
            raise WeatherServiceError(f"Unable to connect to Open-Meteo forecast API: {str(exc)}") from exc
        except Exception as exc:
            if isinstance(exc, WeatherServiceError):
                raise
            logger.error(f"Unexpected error during weather retrieval: {exc}")
            raise WeatherServiceError(f"Failed to process weather data: {str(exc)}") from exc

    def _normalize_weather(self, raw_data: Dict[str, Any], time_scope: str) -> WeatherSnapshot:
        """Normalizes Open-Meteo response into WeatherSnapshot."""
        current = raw_data.get("current", {})
        hourly = raw_data.get("hourly", {})

        # Determine target hour index if time_scope points to future hours today/tomorrow
        target_idx = 0
        times = hourly.get("time", [])

        # Default to current weather values
        from datetime import timezone
        timestamp = current.get("time", datetime.now(timezone.utc).isoformat())
        temp = float(current.get("temperature_2m", 0.0))
        app_temp = float(current.get("apparent_temperature", temp))
        wind = float(current.get("wind_speed_10m", 0.0))
        precip = float(current.get("precipitation", 0.0))
        weather_code = current.get("weather_code")
        rel_hum = current.get("relative_humidity_2m")

        # Derive UV index and precipitation probability from hourly forecast
        # Find index closest to the current time or specified time scope
        uv_index: Optional[float] = None
        precip_prob: Optional[int] = None

        if times:
            now_iso = timestamp[:13] # e.g. "2026-09-22T11"
            matched_indices = [i for i, t in enumerate(times) if t.startswith(now_iso)]
            if matched_indices:
                target_idx = matched_indices[0]

            # Adjust index for specific time scopes if requested
            if "afternoon" in time_scope.lower():
                # Afternoon is typically 14:00 (hour 14)
                afternoon_indices = [i for i, t in enumerate(times[:24]) if "T14:00" in t]
                if afternoon_indices:
                    target_idx = afternoon_indices[0]
            elif "evening" in time_scope.lower():
                # Evening is typically 18:00 (hour 18)
                evening_indices = [i for i, t in enumerate(times[:24]) if "T18:00" in t]
                if evening_indices:
                    target_idx = evening_indices[0]
            elif "tomorrow" in time_scope.lower():
                # Tomorrow midday index
                if len(times) > 36:
                    target_idx = 36

            # If user requested a specific time scope (e.g. this_afternoon, this_evening),
            # read the forecasted values for that time index!
            if time_scope not in ("current", "", None) and target_idx < len(times):
                timestamp = times[target_idx]
                if "temperature_2m" in hourly and target_idx < len(hourly["temperature_2m"]):
                    hourly_temp = hourly["temperature_2m"][target_idx]
                    if hourly_temp is not None:
                        temp = float(hourly_temp)
                if "wind_speed_10m" in hourly and target_idx < len(hourly["wind_speed_10m"]):
                    hourly_wind = hourly["wind_speed_10m"][target_idx]
                    if hourly_wind is not None:
                        wind = float(hourly_wind)
                if "precipitation" in hourly and target_idx < len(hourly["precipitation"]):
                    hourly_precip = hourly["precipitation"][target_idx]
                    if hourly_precip is not None:
                        precip = float(hourly_precip)

            # Extract UV index
            uv_list = hourly.get("uv_index", [])
            if uv_list and target_idx < len(uv_list) and uv_list[target_idx] is not None:
                uv_index = float(uv_list[target_idx])
            elif uv_list:
                # Max UV during the day
                valid_uvs = [u for u in uv_list[:24] if u is not None]
                if valid_uvs:
                    uv_index = float(max(valid_uvs))

            # Extract precipitation probability
            prob_list = hourly.get("precipitation_probability", [])
            if prob_list and target_idx < len(prob_list) and prob_list[target_idx] is not None:
                precip_prob = int(prob_list[target_idx])
            elif prob_list:
                valid_probs = [p for p in prob_list[:24] if p is not None]
                if valid_probs:
                    precip_prob = int(max(valid_probs))

        return WeatherSnapshot(
            timestamp=str(timestamp),
            temperature_c=round(temp, 1),
            apparent_temperature_c=round(app_temp, 1) if app_temp is not None else None,
            wind_speed_kmh=round(wind, 1),
            precipitation_mm=round(precip, 1),
            precipitation_probability=precip_prob,
            uv_index=round(uv_index, 1) if uv_index is not None else None,
            weather_code=weather_code,
            relative_humidity_2m=rel_hum
        )
