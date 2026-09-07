# Intervals.icu MCP Server

Model Context Protocol (MCP) server for connecting Claude and ChatGPT with the Intervals.icu API. It provides tools for retrieving activities, events, wellness data, power curves, and more.

If you find the MCP server useful, please consider supporting its continued development with a donation.

## Prerequisites

Before you begin you'll need your Intervals.icu credentials:

1. **API Key** — Log in to [Intervals.icu](https://intervals.icu), go to **Settings → API**, and generate a new API key.
2. **Athlete ID** — Visible in the URL when you're logged in, e.g. `https://intervals.icu/athlete/i12345/...` → `i12345`.

## Setup — Deploy to FastMCP Cloud (recommended)

The fastest way to get started is to deploy the server to [FastMCP Cloud](https://gofastmcp.com/deployment/fastmcp-cloud) (Prefect Horizon) — a free personal tier, GitHub-connected deploys, and built-in OAuth handling.

### 1. Create the deployment

This repo already includes a [`fastmcp.json`](fastmcp.json) at the root pointing Horizon at the server entrypoint (`src/intervals_mcp_server/server.py:mcp`) and telling it to install dependencies from this project's `pyproject.toml`/`uv.lock`.

1. Sign in at [horizon.prefect.io](https://horizon.prefect.io) (or run `fastmcp login` locally) and connect your GitHub account.
2. Point Horizon at your `intervals-mcp-server` fork/repo and the branch to deploy (`develop`). It detects `fastmcp.json` and builds/deploys automatically; it also redeploys on every push.
3. The dashboard's exact steps may differ from this description — check the [FastMCP Cloud docs](https://gofastmcp.com/deployment/fastmcp-cloud) for the current UI.

### 2. Set Environment Variables

In the Horizon dashboard, add:

| Key | Value | Description |
|-----|-------|-------------|
| `ATHLETE_ID` | `your_athlete_id` | Your Intervals.icu athlete ID (e.g. `i12345`) |
| `API_KEY` | `your_api_key` | Your Intervals.icu API key |

Optional — enable this server's own OAuth 2.0 on top of anything Horizon provides (see [Securing the endpoint](#securing-the-endpoint-oauth)):

| Key | Value | Description |
|-----|-------|-------------|
| `MCP_CLIENT_ID` | `intervals-icu` | OAuth client ID; must match the connector config **exactly** |
| `MCP_CLIENT_SECRET` | `<random secret>` | OAuth client secret / access token; must match the connector |
| `MCP_SERVER_URL` | `https://your-server-name.fastmcp.app` | Public HTTPS URL Horizon assigns (no `/mcp`); required for OAuth discovery |

`MCP_TRANSPORT`/`FASTMCP_HOST`/`FASTMCP_PORT` aren't needed here — `fastmcp.json` already sets `http` transport, and Horizon manages the bind host/port itself.

### 3. Deploy and Verify

1. Trigger the deploy (push to the connected branch, or use the dashboard's deploy action)
2. Note your service URL, e.g. `https://your-server-name.fastmcp.app`
3. Test by opening `https://your-server-name.fastmcp.app/mcp` in a browser — you should get a response from the server

> **⚠️ Security Warning:** Without this server's own OAuth (see below), the endpoint is publicly accessible to anyone who discovers the URL — even behind Horizon's own auth layer, verify what that layer actually restricts before relying on it. Either enable OAuth or do not share your service URL publicly. For full isolation, use the [Local Setup](#local-setup-alternative) (stdio).

> **Known caveat:** `SingleClientOAuthProvider` keeps in-flight authorization codes in memory, which assumes a single long-lived process. If Horizon's free tier scales your deployment across multiple instances or recycles them between the `/authorize` and `/token` requests, the OAuth flow can fail intermittently. Test the full Claude.ai connector flow after deploying, not just `pytest`, before relying on this in practice.

An alternative Docker/Render deployment path is documented below if FastMCP Cloud's OAuth or scaling model doesn't fit your case.

<details>
<summary><strong>Alternative: Deploy to Render (Docker)</strong></summary>

The `Dockerfile` in this repo also works as a self-hosted, single-instance alternative to FastMCP Cloud — useful if you'd rather run a persistent Render/Docker instance than a serverless one.

### 1. Create a Web Service on Render

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repository (`intervals-mcp-server` or your fork)
3. Configure the service:
   - **Name**: `intervals-mcp-server` (or your preferred name)
   - **Branch**: `develop`
   - **Runtime**: **Docker**
   - **Instance Type**: Free tier works fine

> **💤 Free tier cold starts:** Render free-tier services sleep after 15 minutes of inactivity. The first request after sleeping may take 30–60 seconds while the container restarts. Subsequent requests are fast. To avoid this, upgrade to a paid instance or use an external cron/ping service to keep it awake.

### 2. Set Environment Variables

In the Render dashboard under **Environment**, add:

| Key | Value | Description |
|-----|-------|-------------|
| `MCP_TRANSPORT` | `http` | Enables the remote transport (streamable HTTP) |
| `FASTMCP_HOST` | `0.0.0.0` | Bind to all interfaces (required inside Docker) |
| `FASTMCP_PORT` | `8000` | Port the server listens on |
| `ATHLETE_ID` | `your_athlete_id` | Your Intervals.icu athlete ID (e.g. `i12345`) |
| `API_KEY` | `your_api_key` | Your Intervals.icu API key |

Optional — enable OAuth 2.0 to protect the endpoint (see [Securing the endpoint](#securing-the-endpoint-oauth)):

| Key | Value | Description |
|-----|-------|-------------|
| `MCP_CLIENT_ID` | `intervals-icu` | OAuth client ID; must match the connector config **exactly** |
| `MCP_CLIENT_SECRET` | `<random secret>` | OAuth client secret / access token; must match the connector |
| `MCP_SERVER_URL` | `https://your-service-name.onrender.com` | Public HTTPS URL (no `/mcp`); required for OAuth discovery |

### 3. Deploy and Verify

1. Click **Create Web Service** — Render will build the Docker image and deploy
2. Wait for the build to complete (green status)
3. Note your service URL: `https://your-service-name.onrender.com`
4. Test by opening `https://your-service-name.onrender.com/mcp` in a browser — you should get a response from the server

> **⚠️ Security Warning:** Without OAuth (see below), your Render endpoint is publicly accessible — anyone who discovers the URL can query and **mutate** your Intervals.icu data. Either enable OAuth or do not share your service URL publicly. For full isolation, use the [Local Setup](#local-setup-alternative) (stdio).

</details>

### Securing the endpoint (OAuth)

Set `MCP_CLIENT_ID`, `MCP_CLIENT_SECRET`, and `MCP_SERVER_URL` (see table above) to require OAuth 2.0 (authorization code + PKCE) on all HTTP requests. Notes:

- The values on the server must match the connector's OAuth Client ID / Secret **exactly** (case-sensitive).
- `MCP_SERVER_URL` must be the public HTTPS URL **without** `/mcp`; the connector URL must **end** with `/mcp`.
- Leave all three unset to keep the endpoint unauthenticated.

## Connecting Claude

1. Open Claude → **Settings** → **Integrations** (or **MCP Servers**)
2. Click **Add**
3. Fill in:
   - **Name:** `Intervals.icu`
   - **URL:** `https://your-server-name.fastmcp.app/mcp` (must end with `/mcp`)
   - If OAuth is enabled, also set **OAuth Client ID** = `MCP_CLIENT_ID` and **OAuth Client Secret** = `MCP_CLIENT_SECRET` (exact, case-sensitive match)

Open a new conversation and ask "What MCP tools do you have available?" to confirm the connection.

## Connecting ChatGPT

1. In ChatGPT, open **Settings → Features → Custom MCP Connectors** → **Add**
2. Fill in:
   - **Name**: `Intervals.icu`
   - **MCP Server URL**: `https://your-server-name.fastmcp.app/mcp`

Save the connector and open a new chat.

## Available Tools

Once connected, the following tools are available:

**Activities**
- `get_activities` — Retrieve a list of activities
- `get_activity_details` — Get detailed information for a specific activity
- `get_activity_intervals` — Get interval data for a specific activity
- `get_activity_streams` — Get time-series stream data (power, HR, cadence, etc.)
- `get_activity_histogram` — Get a power, heart rate, pace, or gap histogram
- `get_activity_messages` — Get messages/comments on an activity
- `add_activity_message` — Add a message/comment to an activity
- `update_activity`, `delete_activity`, `create_manual_activity`, `bulk_create_manual_activities` — Edit, remove, or create activities

**Activity analysis**
- `get_activity_curve`, `get_activity_best_efforts`, `get_activity_segments`, `get_activity_interval_stats`, `get_activity_map`, `get_activity_power_vs_hr`, `get_activity_hr_load_model`, `get_activity_power_spike_model`, `get_activity_time_at_hr`, `get_activity_weather_summary`

**Activity search & interval editing**
- `search_activities`, `interval_search`, `get_activities_around`, `get_activities_by_ids`, `get_activity_tags`
- `update_activity_intervals`, `update_activity_interval`, `delete_activity_intervals`, `split_activity_interval`

**Events**
- `get_events` — Retrieve upcoming events (workouts, races, etc.)
- `get_event_by_id` — Get detailed information for a specific event
- `add_or_update_event` — Create or update an event
- `delete_event` — Delete a specific event
- `delete_events_by_date_range` — Delete events within a date range

**Wellness & Training**
- `get_wellness_data` — Fetch wellness data
- `get_training_summary` — Get a training load summary
- `get_athlete_power_curves` — Get best power output curves for selected durations and time periods
- `get_athlete_zones` — Get athlete training zones (power, HR, pace, etc.)

**Training Plans**
- `get_training_plan`, `change_training_plan`, `apply_plan_changes`, `apply_plan_to_calendar`, `change_athlete_plans_bulk`

**Custom Items**
- `get_custom_items` — List custom items
- `get_custom_item_by_id` — Get a specific custom item
- `create_custom_item` — Create a new custom item
- `update_custom_item` — Update an existing custom item
- `delete_custom_item` — Delete a custom item

**Workout Library**
- `get_workout_folders` — Get workout library folder metadata (IDs, names, types)
- `list_workouts` — List workouts in the library, optionally filtered by folder
- `get_workout` — Get full workout detail including step-by-step structure
- `create_workout` — Create a new workout in a library folder
- `update_workout` — Update an existing library workout
- `schedule_workout` — Schedule a library workout onto the calendar

> **Structured workouts:** pass steps via `workout_doc`. The server renders them to Intervals.icu workout-builder text so the platform parses them and draws the step chart. Use renderable target units — power `%ftp`/`w`, HR `%hr`/`%lthr`, pace `%pace` or absolute pace (e.g. `4:30/km`); avoid `pace_zone`/`power_zone` for pace runs.

## Troubleshooting Render Deployment

- **Service won't start** — Check Render logs for build errors. Ensure all environment variables are set.
- **Claude/ChatGPT can't connect** — Verify the URL ends with `/mcp` and is publicly accessible. Try opening it in a browser.
- **"Authorization failed" with OAuth** — `MCP_CLIENT_ID`/`MCP_CLIENT_SECRET` must match the connector exactly (case-sensitive), `MCP_SERVER_URL` must be the public HTTPS URL without `/mcp`, and the connector URL must end with `/mcp`. Remove and re-add the connector to clear cached credentials.
- **API errors** — Double-check your `ATHLETE_ID` and `API_KEY` values. Verify your Intervals.icu API key is valid.
- **Free tier cold starts** — Render free-tier services sleep after inactivity. The first request may take 30–60 seconds to wake up.

---

<details>
<summary><strong>Local Setup (alternative)</strong></summary>

If you prefer to run the server on your own machine instead of Render, follow the steps below.

### Requirements

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) (recommended package manager)

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and install

```bash
git clone https://github.com/mvilanova/intervals-mcp-server.git
cd intervals-mcp-server
uv venv --python 3.12
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```
API_KEY=your_intervals_api_key_here
ATHLETE_ID=your_athlete_id_here
```

### Configure Claude Desktop

1. From the project directory, run:

   ```bash
   mcp install src/intervals_mcp_server/server.py --name "Intervals.icu" --with-editable . --env-file .env
   ```

2. Your `claude_desktop_config.json` should look like:

   ```json
   {
     "mcpServers": {
       "Intervals.icu": {
         "command": "/Users/<USERNAME>/.cargo/bin/uv",
         "args": [
           "run",
           "--with", "mcp[cli]",
           "--with-editable", "/path/to/intervals-mcp-server",
           "mcp", "run",
           "/path/to/intervals-mcp-server/src/intervals_mcp_server/server.py"
         ],
         "env": {
           "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
           "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
           "API_KEY": "<YOUR_API_KEY>",
           "LOG_LEVEL": "INFO"
         }
       }
     }
   }
   ```

   Replace `/path/to/` with the actual path. If you see `spawn uv ENOENT` errors, use the full path from `which uv`.

3. Restart Claude Desktop.

### Configure ChatGPT (local)

1. Start the server in HTTP mode:

   ```bash
   export FASTMCP_HOST=127.0.0.1 FASTMCP_PORT=8765 MCP_TRANSPORT=http FASTMCP_LOG_LEVEL=INFO
   python src/intervals_mcp_server/server.py
   ```

2. ChatGPT needs a public URL, so forward the port (e.g. `ngrok http 8765`).

3. In ChatGPT, open **Settings → Features → Custom MCP Connectors** → **Add**:
   - **Name**: `Intervals.icu`
   - **MCP Server URL**: `https://<your-public-host>/mcp`

### Updating

```bash
git checkout main && git pull
source .venv/bin/activate
uv sync
```

If Claude Desktop fails after an update, delete the entry in `claude_desktop_config.json` and re-run the `mcp install` command above.

### Enabling debug logging

Modify `claude_desktop_config.json` to redirect stderr to a log file:

```json
{
  "mcpServers": {
    "Intervals.icu": {
      "command": "/bin/bash",
      "args": [
        "-c",
        "/Users/<USERNAME>/.local/bin/uv run --with 'mcp[cli]' --with-editable /path/to/intervals-mcp-server mcp run /path/to/intervals-mcp-server/src/intervals_mcp_server/server.py 2>> /path/to/intervals-mcp-server/mcp-server.log"
      ],
      "env": {
        "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
        "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
        "API_KEY": "<YOUR_API_KEY>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Then tail the log:

```bash
tail -f /path/to/intervals-mcp-server/mcp-server.log
```

</details>

## Development and testing

Install development dependencies and run the test suite with:

```bash
uv sync --all-extras
pytest -v tests
```

### Running the server locally

```bash
mcp run src/intervals_mcp_server/server.py
```

## License

The GNU General Public License v3.0

## Featured

### Glama.ai

<a href="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server/badge" alt="Intervals.icu Server MCP server" />
</a>
