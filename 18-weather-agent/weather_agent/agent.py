"""Weather Agent.

A pure-Python ADK agent that turns a natural-language question like
"What's the weather in Paris?" into a call to the free, key-less
Open-Meteo API and presents the result. No API key is required.

Tools:
    * ``geocode_city``        - resolve a city name to coordinates.
    * ``get_current_weather`` - fetch current temperature/wind for
                                a (lat, lon) pair.
    * ``get_forecast``        - fetch a short daily forecast.
"""

import json
import urllib.error
import urllib.request
from typing import Dict
from urllib.parse import quote_plus

from google.adk.agents import Agent

_TIMEOUT = 15
_USER_AGENT = "ADK-WeatherAgent/1.0 (+https://example.com)"
_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Tiny inline WMO weather-code lookup so we don't need a third-party
# library to interpret Open-Meteo responses.
_WMO_CODES = {
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
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Light snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with light hail",
    99: "Thunderstorm with heavy hail",
}


def _http_get_json(url: str) -> Dict:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


# --- Tools -------------------------------------------------------------------
def geocode_city(name: str, count: int = 1) -> dict:
    """Resolve a city name to latitude/longitude coordinates.

    Args:
        name:  City name, e.g. ``"Paris"`` or ``"Mumbai, IN"``.
        count: How many matches to return (default 1, max 10).

    Returns:
        A dict with a ``results`` list of ``{name, country, lat, lon}``.
    """
    if not name or not name.strip():
        return {"status": "error", "error": "City name is required."}

    count = max(1, min(int(count), 10))
    url = f"{_GEOCODE_URL}?name={quote_plus(name)}&count={count}"
    try:
        data = _http_get_json(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "error", "error": f"Geocoding failed: {exc}"}

    results = [
        {
            "name": r.get("name"),
            "country": r.get("country"),
            "admin1": r.get("admin1"),
            "lat": r.get("latitude"),
            "lon": r.get("longitude"),
        }
        for r in data.get("results", [])
    ]
    if not results:
        return {"status": "empty", "message": f"No matches for '{name}'.", "results": []}
    return {"status": "ok", "results": results}


def get_current_weather(lat: float, lon: float) -> dict:
    """Fetch the current weather for a latitude/longitude pair.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        A dict with the current temperature, wind, weather code, and
        a human-readable description.
    """
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"status": "error", "error": "lat/lon must be numbers."}

    url = (
        f"{_WEATHER_URL}?latitude={lat_f}&longitude={lon_f}"
        "&current=temperature_2m,wind_speed_10m,weather_code"
    )
    try:
        data = _http_get_json(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "error", "error": f"Weather fetch failed: {exc}"}

    current = data.get("current", {})
    code = current.get("weather_code")
    return {
        "status": "ok",
        "latitude": lat_f,
        "longitude": lon_f,
        "temperature_c": current.get("temperature_2m"),
        "wind_kph": current.get("wind_speed_10m"),
        "weather_code": code,
        "description": _WMO_CODES.get(code, f"Unknown (code {code})"),
        "time": current.get("time"),
    }


def get_forecast(lat: float, lon: float, days: int = 3) -> dict:
    """Return a short daily forecast (max/min temp + precipitation).

    Args:
        lat:   Latitude in decimal degrees.
        lon:   Longitude in decimal degrees.
        days:  Number of forecast days (1-7, default 3).
    """
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"status": "error", "error": "lat/lon must be numbers."}

    days = max(1, min(int(days), 7))
    url = (
        f"{_WEATHER_URL}?latitude={lat_f}&longitude={lon_f}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_sum&forecast_days=7&timezone=auto"
    )
    try:
        data = _http_get_json(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "error", "error": f"Forecast fetch failed: {exc}"}

    daily = data.get("daily", {}) or {}
    rows = []
    for i in range(min(days, len(daily.get("time", [])))):
        code = (daily.get("weather_code") or [None] * 7)[i]
        rows.append({
            "date": daily["time"][i],
            "temp_max_c": daily.get("temperature_2m_max", [None] * 7)[i],
            "temp_min_c": daily.get("temperature_2m_min", [None] * 7)[i],
            "precip_mm":  daily.get("precipitation_sum", [None] * 7)[i],
            "description": _WMO_CODES.get(code, f"Unknown (code {code})"),
        })
    return {"status": "ok", "latitude": lat_f, "longitude": lon_f, "forecast": rows}


# --- Agent definition ---------------------------------------------------------
root_agent = Agent(
    name="weather_agent",
    model="gemini-2.0-flash",
    description=(
        "Looks up the current weather and a short forecast for any "
        "city using the free Open-Meteo API."
    ),
    instruction="""
    You are a friendly weather assistant.

    WORKFLOW:
    1. When the user asks about weather, first call `geocode_city`
       to resolve the place name into (lat, lon).
    2. Then call `get_current_weather` for "now" questions, or
       `get_forecast` for "tomorrow / this week" questions.
    3. Present the answer in a friendly, conversational way. Always
       include units (°C, km/h, mm) and the WMO description.

    RULES:
    - If geocoding returns no results, ask the user to clarify the
       city name (e.g. "Paris, France" vs "Paris, Texas").
    - Never make up temperatures; only report what the API returns.
    - Keep responses under 120 words unless the user asks for detail.
    """,
    tools=[geocode_city, get_current_weather, get_forecast],
)
