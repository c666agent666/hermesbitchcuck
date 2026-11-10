# Hermes Workshare — Handover Document

**Project:** Hermes Workshare Plugin  
**Repo:** https://github.com/c666agent666/hermesbitchcuck  
**Status:** Plugin implemented, validated, tested; end-to-end delegation NOT yet verified live  
**Last Updated:** 2026-11-09  
**Hermes Version:** 0.22.7 (git install)  
**OpenCode Version:** 1.18.4  

---

## What This Plugin Does

Enables **OpenCode (or any MCP client)** to delegate tasks to **Hermes Agent** as a worker harness, while OpenCode keeps its own DeepSeek model for direct chat.

```
User → OpenCode (DeepSeek) ↔ MCP → Hermes Runs API → Hermes Agent (tools, memory, skills)
                                    ↑
                              async, non-blocking
```

**Key principle:** OpenCode stays in charge. Hermes executes delegated jobs only when explicitly invoked via MCP tools.

---

## Repository Structure

```
hermes-workshare/
├── plugin/                     # Native Hermes plugin (loadable)
│   ├── plugin.yaml             # Manifest (provides_tools, config_schema, etc.)
│   └── __init__.py             # register(ctx) — 6 tools + CLI command
├── scripts/
│   └── mcp_server.py           # MCP adapter (HTTP → Hermes Runs API)
├── tests/
│   └── test_plugin.py          # Unit tests (passing)
├── mcp_server_config.json      # OpenCode MCP config reference
├── PLAN.md                     # Build plan & architecture
├── STORYBOARD.md               # 90s demo video storyboard
├── VERIFICATION.md             # Step-by-step E2E verification guide
├── README.md                   # Project overview
└── .gitignore
```

---

## Implemented Components

### 1. Native Hermes Plugin (`plugin/`)
- **Manifest:** `plugin.yaml` — declares 6 tools, config schema, `provides_tools`, `requires_hermes: ">=0.22.7"`
- **Entrypoint:** `plugin/__init__.py` — `register(ctx)` registers:
  - `hermes_workshare_submit_task` — submit async task, returns `run_id`
  - `hermes_workshare_check_status` — poll run status
  - `hermes_workshare_get_results` — retrieve output, usage, runtime
  - `hermes_workshare_steer_task` — mid-run guidance
  - `hermes_workshare_cancel_task` — cancel running task
  - `hermes_workshare_configure` — view/update API URL, key, defaults
- **CLI:** `hermes workshare configure|test`
- **Validation:** `hermes plugins validate` ✅ | `hermes plugins doctor` ✅ (6 tools)

### 2. MCP Adapter (`scripts/mcp_server.py`)
- FastAPI + MCP Streamable HTTP on `http://127.0.0.1:8766/mcp`
- Exposes same 6 tools via MCP `tools/call`
- Config via env: `HERMES_WORKSHARE_API_URL`, `HERMES_WORKSHARE_API_KEY`, `HERMES_WORKSHARE_TIMEOUT`
- Requires: `pip install aiohttp pydantic mcp uvicorn starlette`

### 3. Tests (`tests/test_plugin.py`)
- Plugin registration, config defaults, CLI, MCP config, plugin.yaml — all passing

### 4. Documentation
- `PLAN.md` — architecture, build stages, acceptance criteria
- `STORYBOARD.md` — 90s hackathon demo script
- `VERIFICATION.md` — complete E2E test procedure
- `README.md` — overview with status badges

---

## Current Environment

| Component | Version/Path |
|-----------|--------------|
| Hermes Agent | 0.22.7 (git) at `C:\Users\i\AppData\Local\hermes\hermes-agent` |
| Hermes Home | `C:\Users\i\AppData\Local\hermes` |
| OpenCode | 1.18.4 |
| OpenCode Config | `C:\Users\i\.config\opencode\opencode.json` |
| Plugin Repo | `C:\Users\i\hermes_workspaces\hermes-workshare` |
| Git Remote | `https://github.com/c666agent666/hermesbitchcuck` (main) |
| Hermes Model | DeepSeek V4.1 via OpenRouter (`model.provider=openrouter`, `model.default=deepseek/deepseek-v4.1-flash`) |
| API Server Key | `change...-dev` (in `~/.hermes/.env` as `API_SERVER_KEY`) |

---

## How to Run (Exact Steps)

### Terminal 1 — Hermes Gateway (API Server)
```bash
hermes gateway run
# Wait: "API server listening on http://127.0.0.1:8642"
# Leave running.
```

### Terminal 2 — MCP Adapter
```bash
cd C:\Users\i\hermes_workspaces\hermes-workshare
$env:HERMES_WORKSHARE_API_KEY="change...-dev"   # exact value from ~/.hermes/.env API_SERVER_KEY
$env:HERMES_WORKSHARE_API_URL="http://localhost:8642/v1"
python scripts\mcp_server.py
# Wait: "Starting on http://127.0.0.1:8766/mcp"
# Leave running.
```

### Terminal 3 — OpenCode MCP Setup (run once)
```bash
opencode mcp add hermes-workshare --global --url http://localhost:8766/mcp --header "Authorization: Bearer change...-dev"
opencode mcp list
# Verify: ✓ hermes-workshare  connected
```

### Terminal 4 — Test Delegation
```bash
# 1. Submit
opencode run "Use hermes_submit_task to run: echo 'hello from hermes'"
# → copy run_id from output

# 2. Check status
opencode run "Use hermes_check_status with run_id run_YOUR_ID"

# 3. Get results
opencode run "Use hermes_get_results with run_id run_YOUR_ID"

# 4. Test steer/cancel (optional)
opencode run "Use hermes_steer_task with run_id X guidance 'also print to stdout'"
opencode run "Use hermes_cancel_task with run_id X"
```

---

## Verification Checklist

| Step | Command | Expected |
|------|---------|----------|
| Gateway health | `curl http://localhost:8642/health` | `{"status":"ok"}` |
| Models endpoint | `curl -H "Auth: Bearer KEY" http://localhost:8642/v1/models` | `hermes-agent` listed |
| MCP tools | `curl -H "Auth: Bearer KEY" http://localhost:8766/mcp -d '{"method":"tools/list"}'` | 6 `hermes_*` tools |
| OpenCode MCP | `opencode mcp list` | `✓ hermes-workshare connected` |
| Submit | `opencode run "Use hermes_submit_task..."` | Returns `run_id` immediately |
| Status | `hermes_check_status` | `queued` → `running` → `completed` |
| Results | `hermes_get_results` | Output, `usage`, `runtime.provider/model` |
| Steer | `hermes_steer_task` | Mid-run guidance accepted |
| Cancel | `hermes_cancel_task` | `status: interrupted` |
| Direct chat | `opencode run "2+2="` | Answers via DeepSeek (no tool call) |

---

## Known Gaps / Not Yet Verified

1. **Live end-to-end delegation** — not yet tested with actual running servers
2. **Worktree isolation** — `worktree` parameter accepted but not tested
3. **Idempotency keys** — supported by API but not exercised
4. **Concurrent runs** — concurrency limit behavior untested
5. **Long-running tasks** — timeout/cancel behavior under load unknown
6. **MCP adapter stability** — not stress-tested (connection drops, reconnection)
7. **Authentication** — only tested with static bearer; no OAuth flow
8. **Windows-specific paths** — worktree paths may need escaping

---

## Next Steps (Priority Order)

1. **Run the full verification** (VERIFICATION.md) — confirm every checklist item
2. **Fix any failures** — likely: API key mismatch, port conflicts, missing deps
3. **Test advanced features** — steer, cancel, worktree, concurrent tasks
4. **Record 90s demo** per STORYBOARD.md
4. **Open catalog PR** to `NousResearch/hermes-agent` with pinned commit SHA
5. **Post demo on X** tagging `@NousResearch`
6. **Submit hackathon form** with PR + video links

---

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| MCP "needs authentication" | Header mismatch | Verify `HERMES_WORKSHARE_API_KEY` = `API_SERVER_KEY` exactly |
| Run stuck "queued" | Concurrency limit | `hermes config get platforms.api_server.max_concurrent_runs` |
| Tools missing in OpenCode | Cache/restart needed | Restart OpenCode; ensure `codemode: false` |
| Gateway won't start | Port 8642 in use | `netstat -an | findstr 8642` → kill stale process |
| MCP adapter fails | Missing Python deps | `pip install aiohttp pydantic mcp uvicorn starlette` |
| "API_SERVER_KEY invalid" | Too short/placeholder | `openssl rand -hex 32` → update `.env` + restart gateway |

---

## Key Files to Review

- `plugin/plugin.yaml` — manifest (tools, config, capabilities)
- `plugin/__init__.py` — tool handlers, CLI, config loading
- `scripts/mcp_server.py` — MCP transport, tool mapping
- `VERIFICATION.md` — complete test procedure
- `PLAN.md` — architecture decisions
- `STORYBOARD.md` — demo script

---

## Contact / Context

- **Original ask:** "OpenCode in VS Code uses DeepSeek; offload tasks to Hermes as slave harness"
- **Wrong turns corrected:** 
  - ❌ Changing OpenCode's model to Hermes (breaks primary workflow)
  - ❌ ACP chat panel (not requested; user wants delegation, not second chat)
  - ❌ `hermes proxy` (only supports Nous Portal/xAI, not OpenRouter)
- **Correct approach:** MCP adapter → Hermes Runs API → async delegation tools

---

## If You Pick This Up

1. Start with **VERIFICATION.md** — run every step
2. Check **gateway.log** (`~/.hermes/logs/gateway.log`) for errors
3. The plugin is **catalog-ready** (validation passes); only live testing remains
3. Push fixes to the same repo; update commit SHA in catalog PR
4. Hackathon deadline: check https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission

---

**Last commit:** `31105a7` — Add end-to-end verification guide  
**Branch:** `main`  
**Remote:** `origin` → `https://github.com/c666agent666/hermesbitchcuck`