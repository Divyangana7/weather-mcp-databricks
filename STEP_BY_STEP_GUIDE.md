# Day 3 Homework — Step-by-Step Execution Guide
### Weather-Prediction MCP Server + Agent Bricks agent

This guide walks through every step to build, deploy, and demonstrate the
assignment, and to assemble a submission that a grader can verify. The code is
already written for you in this repo; the steps below tell you what to run,
what to check, and exactly what to screenshot.

---

## 0. Read this first

**A note on the reference material.** This build is aligned to the actual Day 3
repo (`databricks-lakebase-app-day-3`), which splits into a `mcp_server/`
(FastMCP server + broker adapter) and a `dashboard/`, deployed as two separate
Databricks Apps. Your weather build mirrors that: `weather_mcp_server.py`
matches `alpaca_mcp_server.py`, and `weather_broker.py` matches
`alpaca_broker.py`. The agent flow below follows the Day 3 README exactly:
register the MCP server as an external MCP in **AI Gateway**, then build the
agent in **Agent Bricks** (Custom LLM). Sources are listed at the end.

**One thing this assignment does *not* require.** Unlike the Lakebase apps from
Days 1–2, this weather app is **read-only**: the agent reads from a public API
and does not write to a data store. So there is no required "before/after
database" evidence for this homework. Your gradeable evidence is the deployed
app, the tool-call traces, and the agent's answers. (If you do the optional
dashboard that logs queries to Lakebase, that becomes a write path — see
Step 9.)

**Requirements checklist (restated from the assignment).** Tick each as you go:

- [ ] MCP server built with FastMCP, tools exposed via `@mcp.tool`, streamable-HTTP.
- [ ] Separate adapter module holds all HTTP/parsing (no raw `requests` in tools).
- [ ] At least 3 tools: current conditions, forecast, and a derived prediction.
- [ ] The prediction tool applies real logic (threshold), not a passthrough.
- [ ] `requirements.txt` + `app.yaml`; MCP server deployed as its own Databricks App.
- [ ] No secrets committed / no hardcoded keys.
- [ ] A Databricks agent registered against the MCP server as a tool.
- [ ] A clear system prompt (tool routing + guardrails against hallucination).
- [ ] Tool functions have Args/Returns docstrings.
- [ ] Clean error handling (bad location / outage → clean error, not a stack trace).
- [ ] `README.md` (API + auth used, tool list, setup steps).
- [ ] At least 3 natural-language questions demonstrated with tool calls + answers.
- [ ] Public repo link + app URL (or screenshots) submitted.

---

## 1. Get the code onto your machine

You already have this repo. If you are starting from these files, put them in a
folder and confirm the structure matches:

```
weather-mcp-databricks/
├── README.md
├── STEP_BY_STEP_GUIDE.md
├── .gitignore
├── .env.example
├── mcp_server/
│   ├── weather_mcp_server.py    (FastMCP server; mirrors alpaca_mcp_server.py)
│   ├── weather_broker.py        (adapter; mirrors alpaca_broker.py)
│   ├── requirements.txt
│   ├── app.yaml
│   ├── setup_secrets.py        (optional; only for a keyed API)
│   └── test_local.py
└── agent/
    ├── system_prompt.md
    └── tools.md
```

---

## 2. Install dependencies and run the local smoke test

The point of this step is to prove the whole pipeline works **before** you touch
Databricks. This is the fastest way to catch problems.

```bash
cd weather-mcp-databricks/mcp_server
python -m venv .venv && source .venv/bin/activate     # optional but recommended
pip install -r requirements.txt
python test_local.py
```

**What you should see:** four labelled JSON blocks — current weather for
Chicago, a 3-day forecast for Austin, the umbrella logic for tomorrow, and a
clean error for a bad location (a message, not a Python traceback).

**Screenshot #1:** the terminal output of `python test_local.py`. This single
screenshot demonstrates all three required tool paths plus error handling.

> If `get_current_weather` returns an `error`, check your internet connection
> and re-run — Open-Meteo needs no key, so there is nothing to configure.

---

## 3. (Optional) Run the MCP server locally

You can start the server locally to confirm it boots:

```bash
python weather_mcp_server.py
```

It listens on `http://0.0.0.0:8000/mcp`. To poke at the tools interactively,
use the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector
```

Point it at `http://localhost:8000/mcp` (transport: **Streamable HTTP**), click
**List Tools**, and call `get_current_weather` with `location = "Chicago"`.

**Screenshot #2 (nice to have):** MCP Inspector listing your four tools and one
successful tool call.

Stop the server with `Ctrl+C` when done.

---

## 4. Push to a PUBLIC GitHub repo

The submission must be a browsable public repo link, not a zip.

```bash
cd ..                      # back to the repo root
git init
git add .
git commit -m "Day 3: Weather MCP server + agent"
git branch -M main
git remote add origin https://github.com/<your-username>/weather-mcp-databricks.git
git push -u origin main
```

Then, on GitHub:

1. **Settings → General →** confirm the repo visibility is **Public**.
2. Open the repo file tree and confirm there is **no `.env`** and **no API key**
   anywhere. (`.gitignore` already excludes `.env`.)

**Screenshot #3:** the public repo's file tree on GitHub.
**Copy** the repo URL for your submission.

---

## 5. Create a Git folder in Databricks

All of this is in the Databricks workspace UI (no CLI needed), same as Day 1:

1. Sidebar → **Workspace → Create → Git folder** (older UIs: **Repos → Add Repo**).
2. Paste your GitHub repo URL, name the folder, click **Create Git folder**.
   Databricks clones the repo into your workspace.

Whenever you change code later: **Git folder → Pull**, then redeploy the app
(Step 6).

---

## 6. Deploy the MCP server as a Databricks App

1. Sidebar → **Compute → Apps** (or search "Apps").
2. Click **Create app**, choose **Custom** / **From scratch**.
3. Name the app, e.g. `weather-mcp-server` (Day 3 names its equivalent
   `alpaca-paper-mcp`). A `mcp-` prefix is only needed if you register the
   server through the AI Playground's auto-discovery; for the Day 3 AI Gateway
   flow used in Step 8 you paste the URL manually, so any name is fine.
4. For source code, select **Workspace files / Git folder** and browse to the
   **`mcp_server/`** subfolder of your Git folder (the folder containing
   `app.yaml`, `weather_mcp_server.py`, `requirements.txt`).
5. Click **Deploy** (or **Create and deploy**). Databricks reads `app.yaml`,
   installs `requirements.txt`, and runs `python weather_mcp_server.py`. This
   takes a couple of minutes.
6. When status shows **Running**, note the app URL. Your MCP endpoint is:
   `https://<app-url>/mcp`

**Screenshot #4 (required):** the successful deployment page showing the app in
the **Running** state with its URL.

> Deployment troubleshooting: open the app's **Logs** tab. A missing dependency
> means `requirements.txt` wasn't picked up (confirm you pointed the app at the
> `mcp_server/` folder, where `app.yaml` lives). A port error means the process
> isn't binding to `DATABRICKS_APP_PORT`/`0.0.0.0` — the provided
> `weather_mcp_server.py` already does this, so re-pull and redeploy.

---

## 7. (Skip for Open-Meteo) Store a secret — only for a keyed provider

Open-Meteo needs **no key**, so skip this. If you switch to WeatherAPI.com,
store the key as a Databricks secret and read it at runtime (the same
`WorkspaceClient().secrets.get_secret()` pattern Day 3 uses for its Alpaca
keys). Two ways to store it:

- From a notebook: run `python setup_secrets.py`; enter the key when prompted →
  stored as secret `weather/api-key`.
- Or via CLI, matching Day 3's style:
  `databricks secrets put-secret weather api-key --string-value "YOUR_KEY"`.

Then read it in `weather_broker.py` with `_secret("weather", "api-key")`. Never
put the key in `app.yaml`, code, or screenshots.

---

## 8. Register the MCP server as an external MCP (AI Gateway)

This follows the Day 3 README's "Register the MCP server as an external MCP"
step. Your deployed app's MCP endpoint is `https://<app-url>/mcp`.

1. In your workspace, go to **AI Gateway → MCPs → Add MCP**
   (may read **Register external MCP**).
2. Paste your `weather-mcp-server` app URL (the `https://<app-url>/mcp`
   endpoint) as the server endpoint. Transport is **streamable HTTP**.
3. Give it a name, e.g. `weather-mcp`, and save.
4. Databricks introspects the server and lists your tools
   (`get_current_weather`, `get_forecast`, `predict_umbrella_needed`, and the
   stretch `compare_cities`).
5. If prompted, grant your Agent Bricks agent (next step) access to this MCP
   server via Unity Catalog permissions.

**Screenshot #5 (required):** the registered MCP showing your tools discovered.

---

## 9. Build the Agent Bricks agent

This follows the Day 3 README's "Build the Agent Bricks agent" step.

1. Sidebar → **Agents → Agent Bricks → Create agent**.
2. Choose the **Custom LLM** agent type (a single tool-calling agent, which is
   what this is). Multi-agent supervisor also works if you later combine it with
   another agent.
3. Under **Tools**, add the `weather-mcp` MCP server you registered in Step 8
   (all four tools).
4. Paste the system prompt from `agent/system_prompt.md` into the agent's
   system-prompt box.
5. **Evaluate and iterate**: use Agent Bricks' built-in evaluation with a few
   sample prompts (see Step 10) to tune the prompt and tool selection.
6. **Deploy** the agent and open its chat.

**Screenshot #6 (required):** the agent's Tools panel showing the MCP server
attached, with your system prompt visible.

---

## 10. (Optional stretch) Dashboard that logs queries — extra credit

Day 3 ships a second Databricks App, `dashboard/`, deployed from its own
subfolder. For the weather homework the equivalent extra-credit stretch is a
small dashboard app that writes each agent query/prediction to a Lakebase table
and shows recent rows. That introduces a **write path**, so capture before/after
evidence: (a) the table queried before a run, (b) run a query in the app,
(c) the same query showing the new row. This is optional and not needed to pass.

---

## 11. Demonstrate the agent — 3+ questions

In the Agent Bricks chat, run at least three questions that exercise different
tools. Suggested set:

1. **Current:** "What's the weather like right now in Chicago?"
   → expect a `get_current_weather` call.
2. **Forecast:** "What's the 3-day forecast for Austin?"
   → expect a `get_forecast` call.
3. **Prediction:** "Will I need an umbrella in Seattle tomorrow?"
   → expect a `predict_umbrella_needed` call (the agent converts "tomorrow" to a
   date first).
4. *(optional)* **Compare:** "Is it warmer in Miami or Denver right now?"
   → expect a `compare_cities` call.
5. *(optional)* **Error path:** "What's the weather in Xkcdville?"
   → the agent should report it couldn't resolve the location and ask you to
   clarify, rather than inventing weather. This showcases your guardrails.

For each: expand the tool-call trace so both the **tool call** and the
**final answer** are visible.

**Screenshot #7 (required):** at least three Q&A exchanges, each showing the
tool call and the answer. (One screenshot per question is fine.)

---

## 12. Evidence → rubric map (check before you submit)

| Rubric item | Evidence that satisfies it |
|---|---|
| FastMCP server, `@mcp.tool`, streamable-HTTP | `mcp_server/weather_mcp_server.py` in repo; `mcp.run(transport="http", ...)`. |
| Separate adapter module (no `requests` in tools) | `mcp_server/weather_broker.py`; tools only call `wc.*`. |
| 3 required tools | `get_current_weather`, `get_forecast`, `predict_umbrella_needed` in the server file. |
| Prediction applies real logic | `predict_umbrella_needed` uses the 40% threshold; explained in its docstring. |
| `requirements.txt` + `app.yaml`; deployed as its own app | Files in `mcp_server/`; **Screenshot #4** (Running app). |
| No secrets committed / no hardcoded keys | `.gitignore` excludes `.env`; **Screenshot #3** (repo tree). |
| MCP registered as external MCP | **Screenshot #5** (AI Gateway, tools discovered). |
| Agent registered against the MCP server | **Screenshot #6** (Agent Bricks Tools panel). |
| Clear system prompt | `agent/system_prompt.md`; visible in **Screenshot #6**. |
| Docstrings (Args/Returns) | Every tool in `weather_mcp_server.py`. |
| Clean error handling | `WeatherAPIError` → `{"error": ...}`; **Screenshot #1** (bad-location line) and the Step 11 error question. |
| README (API + auth, tools, setup) | `README.md`. |
| 3 NL questions demonstrated | **Screenshot #7**. |
| Public repo + app URL / screenshots | Repo URL from Step 4; app URL from Step 6 (note it may be workspace-restricted, so screenshots are the real evidence). |

**Anything still un-ticked is a gap — fix it before submitting.**

---

## 13. Reflection (draft — personalize the bracketed parts)

> I built a weather MCP server on Databricks using FastMCP, backed by the
> keyless Open-Meteo API. Following the Day 3 pattern, I kept the tool functions
> thin and pushed all the HTTP and parsing into a separate broker adapter, which
> made the tools easy to read and test. The part I found most interesting was
> the prediction tool: instead of returning raw API numbers, it applies a
> precipitation-probability threshold and explains its reasoning, which is what
> turns a data lookup into a recommendation. The trickiest step for me was
> **[e.g. pointing the Databricks App at the right `mcp_server/` subfolder /
> registering the app URL as an external MCP in AI Gateway]**, which I solved by
> **[what you did]**. If I extended this, I would **[e.g. add severe-weather
> alerts via the NWS API / add the dashboard that logs queries to Lakebase]**.
> Overall this clarified how an Agent Bricks agent selects tools from a system
> prompt and how MCP standardizes that connection.

---

## 14. Submit

Include:

1. **Public GitHub repo URL** (from Step 4).
2. **App URL** from Step 6, with a note that it may be workspace-restricted, so
   the screenshots are the evidence.
3. **Screenshots #1, #3, #4, #5, #6, #7** (and #2 if you did the Inspector step).
4. Your **README** (already in the repo) and your **reflection**.

---

## Sources used to build this guide

- **Day 3 reference repo** (`mcp_server/` + `dashboard/` split,
  `alpaca_mcp_server.py` + `alpaca_broker.py`, streamable-HTTP, "Register the
  MCP server as an external MCP" and "Build the Agent Bricks agent" steps):
  EcZachly `databricks-lakebase-app-day-3` README —
  https://github.com/EcZachly/databricks-lakebase-app-day-3
- Instructor's deployment/secret pattern (Git folder + `app.yaml` + Apps UI,
  `setup_secrets.py`): EcZachly `databricks-lakebase-app-day-1` README —
  https://github.com/EcZachly/databricks-lakebase-app-day-1
  and `-day-2` — https://github.com/EcZachly/databricks-lakebase-app-day-2
- Host your own MCP server as a Databricks App (custom MCP, streamable HTTP):
  Databricks docs — https://docs.databricks.com/aws/en/agents/mcp-tools/custom-mcp
  and connect external MCPs — https://docs.databricks.com/aws/en/agents/mcp-tools/connect-external
- FastMCP weather server on a Databricks App, `@mcp.tool`, custom-MCP endpoint
  `https://<app-url>/mcp`, system-prompt example (and the Playground-only `mcp-`
  prefix note): Databricks Community — "Advancing your agentic AI with MCP" —
  https://community.databricks.com/t5/technical-blog/advancing-your-agentic-ai-with-mcp-a-travel-planning-use-case-on/ba-p/144350
- External MCP via UC HTTP connection, Streamable HTTP requirement, proxy URL
  `.../api/2.0/mcp/external/<connection-name>`: Databricks docs —
  https://docs.databricks.com/aws/en/generative-ai/mcp/external-mcp
  and usage — https://docs.databricks.com/aws/en/generative-ai/mcp/external-mcp-usage
- Databricks Apps runtime (`DATABRICKS_APP_PORT`, bind `0.0.0.0`, `app.yaml`
  `command` array, env `valueFrom` secrets): Databricks docs —
  https://docs.databricks.com/aws/en/dev-tools/databricks-apps/system-env
  and app.yaml — https://docs.databricks.com/gcp/en/dev-tools/databricks-apps/app-runtime
- Open-Meteo endpoints/fields (keyless): forecast docs —
  https://open-meteo.com/en/docs ; geocoding docs —
  https://open-meteo.com/en/docs/geocoding-api
- Assignment brief: your Day 3 homework document (in this chat).
