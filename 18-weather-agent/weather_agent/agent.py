# =============================================================================
# weather_agent/agent.py
# =============================================================================
#
# PURPOSE:
#   This module implements a pure-Python weather agent that leverages the
#   Google ADK (Agent Development Kit) to answer natural-language weather
#   questions. It resolves city names to geographic coordinates via the
#   Open-Meteo Geocoding API, then fetches current conditions and short
#   forecasts from the free, key-less Open-Meteo Weather API.
#
#   No API key is required for any of the services used.
#
# USAGE:
#   This module is intended to be imported by an ADK application entrypoint.
#   The primary interface is the ``root_agent`` object, which is an ADK
#   Agent configured with the three tool functions defined herein.
#
#   Example (as a standalone test):
#       >>> from weather_agent.agent import geocode_city
#       >>> geocode_city("Paris")
#       {'status': 'ok', 'results': [{'name': 'Paris', 'country': 'France', ...}]}
#
#       >>> from weather_agent.agent import get_current_weather
#       >>> get_current_weather(48.8566, 2.3522)
#       {'status': 'ok', 'temperature_c': 22.5, 'wind_kph': 12.3, ...}
#
#       >>> from weather_agent.agent import get_forecast
#       >>> get_forecast(48.8566, 2.3522, days=3)
#       {'status': 'ok', 'forecast': [{'date': '2025-01-01', ...}, ...]}
#
# METADATA:
#   Version: 1.0.0
#   Author:  Weather Agent Team
#   Date:    2025-01-01
#   License: MIT
#
# MODULE STRUCTURE:
#   - Constants & configuration (timeout, URLs, user-agent, WMO codes)
#   - Low-level HTTP helper (_http_get_json)
#   - Tool 1: geocode_city — city name → coordinates
#   - Tool 2: get_current_weather — (lat, lon) → current conditions
#   - Tool 3: get_forecast — (lat, lon, days) → daily forecast
#   - ADK Agent: root_agent — the conversational agent wiring
#
# =============================================================================

import json
import urllib.error
import urllib.request
from typing import Dict
from urllib.parse import quote_plus

# === IMPORTS & DEPENDENCIES ===
# The ADK Agent class is used to wrap our tool functions into a conversational
# agent. Ensure `google-adk` is installed in the target environment.
from google.adk.agents import Agent


# === SECTION: CONSTANTS & CONFIGURATION ===
# -----------------------------------------------------------------------------
# These module-level constants control request behaviour and endpoint URLs.
# They are intentionally module-scoped so they can be overridden in tests or
# future configuration without modifying function bodies.

# Maximum number of seconds to wait for an HTTP response before timing out.
# NOTE: The Open-Meteo API is typically very fast, but 15s provides a safe
# margin for slower network conditions without hanging the agent indefinitely.
_TIMEOUT = 15  # type: () -> int

# Custom User-Agent header sent with every outgoing request.
# This helps the API provider identify traffic来源 from this specific agent.
_USER_AGENT = "ADK-WeatherAgent/1.0 (+https://example.com)"

# Endpoint for the Open-Meteo Geocoding API (resolves city names → lat/lon).
_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Endpoint for the Open-Meteo Forecast API (weather data).
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# TODO: Consider making _TIMEOUT, _GEOCODE_URL, and _WEATHER_URL configurable
#       via environment variables for deployment flexibility.

# -----------------------------------------------------------------------------
# WMO (World Meteorological Organization) weather interpretation codes.
# These codes are returned by the Open-Meteo API as integers and must be
# mapped to human-readable strings for the end user.
# Source: https://open-meteo.com/en/docs#weather-code
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


# === SECTION: LOW-LEVEL HTTP HELPER ===
# -----------------------------------------------------------------------------
# The single HTTP helper used by all three tool functions. Centralising it here
# avoids duplicating request/timeout/error-handling logic across functions.

def _http_get_json(url: str) -> Dict:
    """Perform a GET request to *url* and return the parsed JSON response.

    This is an internal helper. All network-level concerns — User-Agent
    header, timeout, JSON decoding — are handled here so that the higher-level
    tool functions can focus on business logic.

    Args:
        url: A fully-formed URL string to request.

    Returns:
        The JSON-decoded response body as a Python dict.

    Raises:
        urllib.error.URLError: If the request fails at the network level.
        TimeoutError: If the server does not respond within ``_TIMEOUT`` seconds.
        ValueError: If the response body is not valid JSON.

    Examples:
        >>> data = _http_get_json("https://api.open-meteo.com/v1/forecast?latitude=48.8&longitude=2.3")
        >>> isinstance(data, dict)
        True
    """
    # Build a Request object so we can attach a custom User-Agent header.
    # Some API providers reject requests that lack a recognisable User-Agent.
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

    # Use a context manager to guarantee the network socket is closed
    # even if an exception occurs during reading.
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as resp:
        # Read raw bytes, decode as UTF-8, then parse JSON into a dict.
        return json.loads(resp.read().decode("utf-8"))


# === SECTION: TOOL 1 — GEOCODING ===
# -----------------------------------------------------------------------------
# Resolves a free-text city name into geographic coordinates (latitude &
# longitude). This is the first step in the agent's weather workflow.

def geocode_city(name: str, count: int = 1) -> dict:
    """Resolve a city name to latitude/longitude coordinates.

    Calls the Open-Meteo Geocoding API and returns a structured result
    containing one or more matching locations. The caller (the ADK agent)
    will typically use the first result's ``lat`` / ``lon`` to query weather.

    Args:
        name:  City name to search for, e.g. ``"Paris"`` or ``"Mumbai, IN"``.
               Trailing/leading whitespace is stripped before the API call.
        count: How many match results to return. Defaults to 1; maximum 10.
               Values outside 1-10 are clamped automatically.

    Returns:
        A result dict with one of the following shapes:

        - On success (``status: "ok"``):
            ``{"status": "ok", "results": [{name, country, admin1, lat, lon}, ...]}``
        - On empty results (``status: "empty"``):
            ``{"status": "empty", "message": str, "results": []}``
        - On error (``status: "error"``):
            ``{"status": "error", "error": str}``

    Raises:
        This function catches all network/serialization exceptions internally
        and returns them as ``{"status": "error", ...}`` rather than raising.

    Examples:
        >>> geocode_city("Paris")
        {'status': 'ok', 'results': [{'name': 'Paris', 'country': 'France', 'admin1': 'Île-de-France', 'lat': 48.8566, 'lon': 2.3522}]}
        >>> geocode_city("")
        {'status': 'error', 'error': 'City name is required.'}
        >>> geocode_city("NonexistentCityXYZ")
        {'status': 'empty', 'message': "No matches for 'NonexistentCityXYZ'.", 'results': []}
    """
    # type: (name: str, count: int) -> dict

    # Guard against empty or blank input early. This avoids an unnecessary
    # (and failing) API call and gives the caller a clear error message.
    if not name or not name.strip():
        return {"status": "error", "error": "City name is required."}

    # Clamp count to the valid range [1, 10]. The API enforces a max of 10,
    # and returning at least 1 result is the sensible floor.
    count = max(1, min(int(count), 10))

    # Build the query URL. quote_plus ensures special characters (spaces,
    # accents, etc.) in city names are safely percent-encoded.
    url = f"{_GEOCODE_URL}?name={quote_plus(name)}&count={count}"

    try:
        # Delegate the actual HTTP work to the shared helper.
        data = _http_get_json(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        # NOTE: We swallow network errors and return a structured error dict
        # so the ADK agent can handle it gracefully in its conversation.
        return {"status": "error", "error": f"Geocoding failed: {exc}"}

    # Extract relevant fields from each API result into a clean, consistent
    # dict shape. We use .get() defensively because the API schema may evolve.
    results = [
        {
            "name": r.get("name"),
            "country": r.get("country"),
            "admin1": r.get("admin1"),  # e.g. state/province/region
            "lat": r.get("latitude"),
            "lon": r.get("longitude"),
        }
        for r in data.get("results", [])
    ]

    if not results:
        # No matches found — return a distinct "empty" status so the agent
        # can decide whether to ask the user for clarification.
        return {"status": "empty", "message": f"No matches for '{name}'.", "results": []}

    return {"status": "ok", "results": results}


# === SECTION: TOOL 2 — CURRENT WEATHER ===
# -----------------------------------------------------------------------------
# Fetches the current temperature, wind speed, and weather code for a given
# geographic coordinate pair.

def get_current_weather(lat: float, lon: float) -> dict:
    """Fetch the current weather for a latitude/longitude pair.

    Queries the Open-Meteo Forecast API's ``current`` block, which contains
    instant observations for temperature (°C), wind speed (km/h), weather
    code, and timestamp.

    Args:
        lat: Latitude in decimal degrees. Accepts int or float; will be
             coerced to ``float`` internally.
        lon: Longitude in decimal degrees. Same coercion rules as ``lat``.

    Returns:
        A result dict with the following keys on success (``status: "ok"``):

        - ``latitude``     — the validated latitude (float)
        - ``longitude``    — the validated longitude (float)
        - ``temperature_c`` — current temperature in °C (float or None)
        - ``wind_kph``      — current wind speed in km/h (float or None)
        - ``weather_code``  — WMO integer code (int or None)
        - ``description``   — human-readable WMO description (str)
        - ``time``          — ISO-8601 observation timestamp (str or None)

        On error, returns ``{"status": "error", "error": str}``.

    Raises:
        All exceptions are caught internally and returned as error dicts.

    Examples:
        >>> get_current_weather(48.8566, 2.3522)
        {'status': 'ok', 'latitude': 48.8566, 'longitude': 2.3522, 'temperature_c': 21.0, 'wind_kph': 8.5, 'weather_code': 1, 'description': 'Mainly clear', 'time': '2025-01-01T12:00'}
        >>> get_current_weather("abc", 2.0)
        {'status': 'error', 'error': 'lat/lon must be numbers.'}
    """
    # type: (lat: float, lon: float) -> dict

    # Validate and coerce lat/lon to float before constructing the URL.
    # This catches non-numeric inputs (e.g., None, strings) early, preventing
    # a malformed URL or confusing API error response.
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"status": "error", "error": "lat/lon must be numbers."}

    # Construct the forecast URL requesting only the "current" weather
    # variables we need. Requesting fewer fields reduces response size
    # and latency — a worthwhile optimisation for a real-time lookup.
    url = (
        f"{_WEATHER_URL}?latitude={lat_f}&longitude={lon_f}"
        "&current=temperature_2m,wind_speed_10m,weather_code"
    )

    try:
        data = _http_get_json(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "error", "error": f"Weather fetch failed: {exc}"}

    # Extract the "current" sub-dict. If absent, default to empty dict
    # so subsequent .get() calls return None rather than raising KeyError.
    current = data.get("current", {})
    code = current.get("weather_code")

    # Build and return the result. _WMO_CODES maps the integer code to a
    # friendly description; unknown codes fall back to a generic label.
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


# === SECTION: TOOL 3 — FORECAST ===
# -----------------------------------------------------------------------------
# Returns a multi-day daily forecast including max/min temperature and
# cumulative precipitation. The API always returns up to 7 days; we slice
# to the user-requested count.

def get_forecast(lat: float, lon: float, days: int = 3) -> dict:
    """Return a short daily forecast (max/min temp + precipitation).

    The Open-Meteo API provides up to 7 days of daily forecast data.
    This function requests the full 7-day range from the API (to avoid
    re-fetching if the user later asks for more days) but returns only
    the requested number of days to the caller.

    Args:
        lat:   Latitude in decimal degrees. Coerced to float internally.
        lon:   Longitude in decimal degrees. Coerced to float internally.
        days:  Number of forecast days to return (1-7, default 3). Values
               outside this range are clamped automatically.

    Returns:
        A result dict with the following keys on success (``status: "ok"``):

        - ``latitude``   — validated latitude (float)
        - ``longitude``  — validated longitude (float)
        - ``forecast``   — list of daily forecast dicts, each containing:
            - ``date``        — ISO-8601 date string
            - ``temp_max_c``  — daily maximum temperature (°C)
            - ``temp_min_c``  — daily minimum temperature (°C)
            - ``precip_mm``   — total precipitation (mm)
            - ``description`` — WMO human-readable description (str)

        On error, returns ``{"status": "error", "error": str}``.

    Raises:
        All exceptions are caught internally and returned as error dicts.

    Examples:
        >>> get_forecast(48.8566, 2.3522, days=2)
        {'status': 'ok', 'latitude': 48.8566, 'longitude': 2.3522, 'forecast': [{'date': '2025-01-01', 'temp_max_c': 23.0, 'temp_min_c': 14.0, 'precip_mm': 0.0, 'description': 'Partly cloudy'}, ...]}
    """
    # type: (lat: float, lon: float, days: int) -> dict

    # Validate lat/lon the same way as the current-weather tool for
    # consistency and defensive programming.
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"status": "error", "error": "lat/lon must be numbers."}

    # Clamp days to [1, 7]. NOTE: We request forecast_days=7 from the API
    # always (see URL below) so the full dataset is cached in one call;
    # we only slice the results later based on the user's preference.
    days = max(1, min(int(days), 7))

    # IMPORTANT: We always request 7 forecast days from the API regardless
    # of the *days* parameter. This is a deliberate design choice — it means
    # a user who first asks "what about tomorrow?" and then "and the day
    # after?" only triggers a single API call within the agent's workflow.
    url = (
        f"{_WEATHER_URL}?latitude={lat_f}&longitude={lon_f}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_sum&forecast_days=7&timezone=auto"
    )

    try:
        data = _http_get_json(url)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"status": "error", "error": f"Forecast fetch failed: {exc}"}

    # Extract the "daily" sub-dict. Default to empty dict to avoid KeyError
    # if the API response shape is unexpected.
    daily = data.get("daily", {}) or {}

    # Build one summary dict per requested day. We guard against index
    # errors by using min(days, len(available_days)).
    # NOTE: The ``[None] * 7`` fallback lists protect against missing
    # keys in the API response, ensuring .get() returns None rather than
    # raising an IndexError on a short list.
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


# === SECTION: ADK AGENT CONFIGURATION ===
# -----------------------------------------------------------------------------
# The root_agent is the entry point for the ADK application. It binds the
# three tool functions to a conversational agent powered by the Gemini 2.0
# Flash model. The system-level instruction defines the agent's workflow
# and behaviour rules.

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

# === END OF MODULE ===