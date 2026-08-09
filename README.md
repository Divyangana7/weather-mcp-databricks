# Weather-Prediction MCP Server + Agent (Day 3)

A custom **Model Context Protocol (MCP)** server that exposes weather-forecast
tools, plus a Databricks agent that uses those tools to answer natural-language
weather questions. Built as a Databricks App, following the Day 3 reference
pattern (`mcp_server/` FastMCP server + adapter module split).

## Weather API + auth

- **Provider:** [Open-Meteo](https://open-meteo.com) — free, **no API key, no
  sign-up**. Non-commercial use up to ~10,000 calls/day.
- **Auth:** none required. Because Open-Meteo is keyless, no Databricks secret
  is needed. A `_secret()` helper and `setup_secrets.py` are included for the
  case where you swap in a keyed provider (e.g. WeatherAPI.com) — the key is
  then read at runtime, never hardcoded or committed.

## Architecture

```
User ──▶ Databricks Agent (LLM + system prompt)
             │  tool calls (MCP)
             ▼
   Weather MCP server  ── Databricks App ──▶  https://<app-url>/mcp
             │  (thin @mcp.tool functions)
             ▼
   weather_broker.py  (adapter: all HTTP + parsing)
             │
             ▼
   Open-Meteo  (geocoding + forecast APIs)
```

## Tools

| Tool | What it does |
|------|--------------|
| `get_current_weather(location)` | Current temp, conditions, humidity, wind. |
| `get_forecast(location, days=3)` | Daily highs/lows, precip chance, conditions. |
| `predict_umbrella_needed(location, date)` | Derived call: umbrella recommended if day's precip probability ≥ 40%. |
| `compare_cities(a, b)` *(stretch)* | Which of two cities is warmer / wetter now. |

`get_current_weather`, `get_forecast`, and `predict_umbrella_needed` are the
three required tools. The umbrella tool applies a threshold and explains its
reasoning rather than echoing raw API output.

## Files

```
mcp_server/
  weather_mcp_server.py   # FastMCP server; thin @mcp.tool functions (mirrors alpaca_mcp_server.py)
  weather_broker.py       # adapter: geocoding + forecast HTTP calls + parsing (mirrors alpaca_broker.py)
  requirements.txt        # fastmcp, requests, databricks-sdk
  app.yaml                # Databricks App runtime config
  setup_secrets.py        # OPTIONAL: only for a keyed provider
  test_local.py           # local smoke test (proves the pipeline before deploy)
agent/
  system_prompt.md        # agent system prompt (guardrails + tool routing)
  tools.md                # tool list + how the MCP server is registered
.env.example              # local env template (no real secrets)
.gitignore                # ignores .env and caches
```

## Setup (summary)

1. `pip install -r mcp_server/requirements.txt`
2. `python mcp_server/test_local.py` — confirm the adapter works locally.
3. Push this repo to a **public** GitHub repo (confirm no secrets committed).
4. In Databricks: create a **Git folder** from the repo, then create a
   **Databricks App** pointing at `mcp_server/`. The MCP endpoint is
   `https://<app-url>/mcp`.
5. Register that URL as an **external MCP** in **AI Gateway**, then build an
   **Agent Bricks** agent (Custom LLM), add the MCP server under Tools, set the
   system prompt from `agent/system_prompt.md`, and test with natural-language
   questions.

Full instructions are in `STEP_BY_STEP_GUIDE.md`.

## Notes

- Endpoint transport is streamable HTTP (required for Databricks custom MCP
  servers). The server binds to `0.0.0.0` and the `DATABRICKS_APP_PORT` the
  Apps runtime injects.
- No secrets are committed. Keep any keyed-provider key in a Databricks secret.
