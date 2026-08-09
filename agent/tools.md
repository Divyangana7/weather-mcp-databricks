# Agent Tool List & Configuration

**MCP server (custom, hosted as a Databricks App)**
Endpoint: `https://<your-mcp-app-url>/mcp`

| Tool | Signature | Purpose |
|------|-----------|---------|
| `get_current_weather` | `(location: str)` | Current conditions (required tool #1) |
| `get_forecast` | `(location: str, days: int = 3)` | Multi-day forecast (required tool #2) |
| `predict_umbrella_needed` | `(location: str, date: str)` | Derived recommendation, precip-prob ≥ 40% rule (required tool #3) |
| `compare_cities` | `(location_a: str, location_b: str)` | Stretch tool (extra credit) |

**How it is registered for the agent** (Day 3 flow)
1. Deploy `mcp_server/` as a Databricks App → endpoint `https://<app-url>/mcp`.
2. **AI Gateway → MCPs → Add MCP**: paste the app URL (streamable HTTP), name it
   (e.g. `weather-mcp`). Databricks introspects and lists the tools.
3. **Agents → Agent Bricks → Create agent → Custom LLM**: under **Tools**, add
   the `weather-mcp` server; paste the system prompt from `system_prompt.md`.

**LLM endpoint:** any Databricks foundation-model endpoint available in your
workspace.

**System prompt:** see `system_prompt.md`.
