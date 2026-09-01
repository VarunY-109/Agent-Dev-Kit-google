# Weather Agent

A pure-Python ADK agent that answers "What's the weather in *X*?"
questions by calling the free, **no API key required**
[Open-Meteo](https://open-meteo.com) service.

## Tools

| Tool | Purpose |
| --- | --- |
| `geocode_city(name, count=1)` | Resolve a city name to coordinates. |
| `get_current_weather(lat, lon)` | Current temperature, wind, weather code. |
| `get_forecast(lat, lon, days=3)` | Daily max/min/precipitation for up to 7 days. |

A small WMO weather-code lookup table (built into `agent.py`) turns
the numeric code into a human-readable description so the agent
doesn't need a third-party weather library.

## Project Structure

```
18-weather-agent/
└── weather_agent/
    ├── __init__.py        # re-exports the agent
    ├── agent.py           # root_agent + Open-Meteo tools
    └── .env.example       # GOOGLE_API_KEY template
```

## Getting Started

1. Activate the root virtual environment:
   ```bash
   source ../.venv/bin/activate
   ```
2. Copy `.env.example` to `.env` and set `GOOGLE_API_KEY`.
3. Launch the UI:
   ```bash
   adk web
   ```
4. Select **weather_agent** from the dropdown.

## Example Prompts to Try

- "What's the weather in Bengaluru right now?"
- "Give me a 5-day forecast for Tokyo."
- "Is it going to rain in London this week?"
