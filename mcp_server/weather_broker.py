"""
weather_broker.py
-----------------
Adapter / broker module for the Weather MCP server.

This module plays the same role as `alpaca_broker.py` in the Day 3 reference
repo: ALL outbound HTTP calls and response parsing live here. The MCP tool
functions in `weather_mcp_server.py` stay thin and only call into this module.

Data source: Open-Meteo (https://open-meteo.com) — no API key, no sign-up.
  - Geocoding:  https://geocoding-api.open-meteo.com/v1/search
  - Forecast:   https://api.open-meteo.com/v1/forecast

If you switch to a keyed provider (e.g. WeatherAPI.com), read the key with the
`_secret()` helper below (mirrors the WorkspaceClient().secrets.get_secret()
pattern in the reference `alpaca_broker.py`) instead of hardcoding it.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HTTP_TIMEOUT = 10  # seconds

# WMO weather interpretation codes -> human-readable text.
# Reference: Open-Meteo docs (weather_code variable).
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherAPIError(Exception):
    """Raised for any weather/geocoding failure so callers can return a clean
    error instead of leaking a stack trace to the agent."""


# --------------------------------------------------------------------------- #
# Secret helper (only needed for keyed providers; unused for Open-Meteo)
# --------------------------------------------------------------------------- #
def _secret(scope: str, key: str) -> Optional[str]:
    """Fetch a Databricks secret at runtime (same idea as `_secret()` in the
    reference `alpaca_broker.py`). Returns None if unavailable so the
    keyless Open-Meteo path keeps working locally and in the app.

    Do NOT hardcode API keys. Store them with `setup_secrets.py`.
    """
    try:
        from databricks.sdk import WorkspaceClient

        return WorkspaceClient().secrets.get_secret(scope=scope, key=key).value
    except Exception:
        return None


def _condition(code: Optional[int]) -> str:
    """Translate a WMO weather code into readable text."""
    if code is None:
        return "Unknown"
    return WMO_CODES.get(int(code), f"Unknown (code {code})")


# --------------------------------------------------------------------------- #
# Location resolution
# --------------------------------------------------------------------------- #
def geocode(location: str) -> dict:
    """Resolve a location string to coordinates.

    Accepts either:
      * a city name (e.g. "Chicago", "Austin, TX"), or
      * a "lat,lon" pair (e.g. "41.88,-87.63").

    Returns a dict: {latitude, longitude, resolved_name, country, timezone}.
    Raises WeatherAPIError if the location cannot be resolved.
    """
    if not location or not location.strip():
        raise WeatherAPIError("No location provided.")

    text = location.strip()

    # Direct "lat,lon" input.
    if "," in text:
        parts = [p.strip() for p in text.split(",")]
        if len(parts) == 2:
            try:
                lat, lon = float(parts[0]), float(parts[1])
                return {
                    "latitude": lat,
                    "longitude": lon,
                    "resolved_name": f"{lat},{lon}",
                    "country": None,
                    "timezone": "auto",
                }
            except ValueError:
                pass  # Not numeric -> treat as "City, Region" and geocode below.

    params = {"name": text, "count": 1, "language": "en", "format": "json"}
    try:
        resp = requests.get(GEOCODING_URL, params=params, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise WeatherAPIError(f"Geocoding request failed: {exc}") from exc

    if resp.status_code != 200:
        raise WeatherAPIError(
            f"Geocoding API returned HTTP {resp.status_code} for '{text}'."
        )

    results = (resp.json() or {}).get("results")
    if not results:
        raise WeatherAPIError(
            f"Could not resolve location '{text}'. Try a more specific city name."
        )

    top = results[0]
    return {
        "latitude": top["latitude"],
        "longitude": top["longitude"],
        "resolved_name": top.get("name", text),
        "country": top.get("country"),
        "timezone": top.get("timezone", "auto"),
    }


def _get_forecast_json(latitude: float, longitude: float, **extra) -> dict:
    """Low-level call to the Open-Meteo forecast endpoint."""
    params = {"latitude": latitude, "longitude": longitude, "timezone": "auto"}
    params.update(extra)
    try:
        resp = requests.get(FORECAST_URL, params=params, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise WeatherAPIError(f"Forecast request failed: {exc}") from exc

    if resp.status_code != 200:
        raise WeatherAPIError(f"Forecast API returned HTTP {resp.status_code}.")
    return resp.json() or {}


# --------------------------------------------------------------------------- #
# Public functions used by the MCP tools
# --------------------------------------------------------------------------- #
def fetch_current(location: str) -> dict:
    """Return current conditions for a location as a clean dict."""
    loc = geocode(location)
    data = _get_forecast_json(
        loc["latitude"],
        loc["longitude"],
        current=",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
            ]
        ),
    )
    cur = data.get("current", {})
    units = data.get("current_units", {})
    return {
        "location": loc["resolved_name"],
        "country": loc["country"],
        "observed_at": cur.get("time"),
        "temperature": cur.get("temperature_2m"),
        "feels_like": cur.get("apparent_temperature"),
        "humidity_pct": cur.get("relative_humidity_2m"),
        "precipitation": cur.get("precipitation"),
        "wind_speed": cur.get("wind_speed_10m"),
        "conditions": _condition(cur.get("weather_code")),
        "units": {
            "temperature": units.get("temperature_2m", "°C"),
            "wind_speed": units.get("wind_speed_10m", "km/h"),
            "precipitation": units.get("precipitation", "mm"),
        },
    }


def fetch_forecast(location: str, days: int = 3) -> dict:
    """Return an N-day daily forecast for a location as a clean dict."""
    days = max(1, min(int(days), 16))  # Open-Meteo supports up to 16 days.
    loc = geocode(location)
    data = _get_forecast_json(
        loc["latitude"],
        loc["longitude"],
        forecast_days=days,
        daily=",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "precipitation_sum",
                "wind_speed_10m_max",
            ]
        ),
    )
    daily = data.get("daily", {})
    times = daily.get("time", []) or []
    out = []
    for i, day in enumerate(times):
        out.append(
            {
                "date": day,
                "conditions": _condition(_index(daily.get("weather_code"), i)),
                "temp_high": _index(daily.get("temperature_2m_max"), i),
                "temp_low": _index(daily.get("temperature_2m_min"), i),
                "precip_chance_pct": _index(
                    daily.get("precipitation_probability_max"), i
                ),
                "precip_sum": _index(daily.get("precipitation_sum"), i),
                "wind_max": _index(daily.get("wind_speed_10m_max"), i),
            }
        )
    return {
        "location": loc["resolved_name"],
        "country": loc["country"],
        "days": out,
    }


def _index(seq, i):
    """Safe list indexing helper (returns None if missing)."""
    if seq is None or i >= len(seq):
        return None
    return seq[i]
