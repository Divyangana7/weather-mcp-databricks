"""
weather_mcp_server.py
---------------------
FastMCP server that exposes weather tools over the streamable-HTTP transport,
following the same pattern as `mcp_server/alpaca_mcp_server.py` in the Day 3
reference repo (thin @mcp.tool functions that wrap a broker adapter).

Tools (minimum 3 required):
  1. get_current_weather(location)        -> current conditions
  2. get_forecast(location, days)         -> multi-day forecast
  3. predict_umbrella_needed(location, date) -> derived recommendation (reasoning)

Stretch (extra credit):
  4. compare_cities(location_a, location_b)  -> which city is warmer / wetter

All HTTP/parsing lives in `weather_broker.py`. The tool functions below only
orchestrate and format, and they convert any WeatherAPIError into a clean
error dict so the agent never sees a stack trace.

Deployed as a Databricks App. The Databricks Apps runtime injects
DATABRICKS_APP_PORT and expects the process to listen on 0.0.0.0. The MCP
endpoint is exposed at:  https://<app-url>/mcp
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

import weather_broker as wc

mcp = FastMCP("weather")

# Precipitation-probability threshold (percent) at/above which an umbrella is
# recommended. Documented here and in the tool docstring so the logic is
# transparent and gradeable.
UMBRELLA_THRESHOLD_PCT = 40


@mcp.tool
def get_current_weather(location: str) -> dict:
    """Get current weather conditions for a location.

    Args:
        location: City name (e.g. "Chicago", "Austin, TX") or a "lat,lon" pair
                  (e.g. "41.88,-87.63").

    Returns:
        dict: {location, country, observed_at, temperature, feels_like,
               humidity_pct, precipitation, wind_speed, conditions, units}
        On failure: {"error": "<clean message>"}.
    """
    try:
        return wc.fetch_current(location)
    except wc.WeatherAPIError as exc:
        return {"error": str(exc)}


@mcp.tool
def get_forecast(location: str, days: int = 3) -> dict:
    """Get a multi-day daily forecast for a location.

    Args:
        location: City name or "lat,lon" pair.
        days: Number of days to forecast (1-16). Defaults to 3.

    Returns:
        dict: {location, country, days: [{date, conditions, temp_high,
               temp_low, precip_chance_pct, precip_sum, wind_max}, ...]}
        On failure: {"error": "<clean message>"}.
    """
    try:
        return wc.fetch_forecast(location, days)
    except wc.WeatherAPIError as exc:
        return {"error": str(exc)}


@mcp.tool
def predict_umbrella_needed(location: str, date: str) -> dict:
    """Decide whether an umbrella is likely needed on a given date.

    This is a derived judgment, not a passthrough of the raw API. Rule:
    an umbrella is recommended when the day's maximum precipitation
    probability is at or above UMBRELLA_THRESHOLD_PCT (40%).

    Args:
        location: City name or "lat,lon" pair.
        date: Target date in YYYY-MM-DD format (must fall within the next
              16 days).

    Returns:
        dict: {location, date, umbrella_recommended (bool), precip_chance_pct,
               threshold_pct, conditions, reason}
        On failure: {"error": "<clean message>"}.
    """
    try:
        forecast = wc.fetch_forecast(location, days=16)
    except wc.WeatherAPIError as exc:
        return {"error": str(exc)}

    match = next((d for d in forecast["days"] if d["date"] == date), None)
    if match is None:
        available = [d["date"] for d in forecast["days"]]
        return {
            "error": (
                f"No forecast available for {date}. "
                f"Available dates: {available[0]} to {available[-1]}."
                if available
                else f"No forecast available for {date}."
            )
        }

    chance = match["precip_chance_pct"]
    if chance is None:
        return {"error": f"Precipitation probability unavailable for {date}."}

    recommended = chance >= UMBRELLA_THRESHOLD_PCT
    reason = (
        f"Max precipitation chance for {date} is {chance}%, which is "
        f"{'at or above' if recommended else 'below'} the "
        f"{UMBRELLA_THRESHOLD_PCT}% threshold."
    )
    return {
        "location": forecast["location"],
        "date": date,
        "umbrella_recommended": recommended,
        "precip_chance_pct": chance,
        "threshold_pct": UMBRELLA_THRESHOLD_PCT,
        "conditions": match["conditions"],
        "reason": reason,
    }


@mcp.tool
def compare_cities(location_a: str, location_b: str) -> dict:
    """(Stretch) Compare current weather between two cities.

    Args:
        location_a: First city name or "lat,lon" pair.
        location_b: Second city name or "lat,lon" pair.

    Returns:
        dict: {city_a, city_b, warmer, wetter} where each value summarizes the
              comparison. On failure: {"error": "<clean message>"}.
    """
    try:
        a = wc.fetch_current(location_a)
        b = wc.fetch_current(location_b)
    except wc.WeatherAPIError as exc:
        return {"error": str(exc)}

    def warmer(x, y):
        if x["temperature"] is None or y["temperature"] is None:
            return "unknown"
        if x["temperature"] == y["temperature"]:
            return "tie"
        return x["location"] if x["temperature"] > y["temperature"] else y["location"]

    def wetter(x, y):
        px = x.get("precipitation") or 0
        py = y.get("precipitation") or 0
        if px == py:
            return "tie"
        return x["location"] if px > py else y["location"]

    return {
        "city_a": {"location": a["location"], "temperature": a["temperature"],
                   "conditions": a["conditions"]},
        "city_b": {"location": b["location"], "temperature": b["temperature"],
                   "conditions": b["conditions"]},
        "warmer": warmer(a, b),
        "wetter": wetter(a, b),
    }


if __name__ == "__main__":
    # Databricks Apps injects DATABRICKS_APP_PORT and expects host 0.0.0.0.
    # Falls back to 8000 for local runs.
    port = int(os.environ.get("DATABRICKS_APP_PORT", "8000"))
    mcp.run(transport="http", host="0.0.0.0", port=port, path="/mcp")
