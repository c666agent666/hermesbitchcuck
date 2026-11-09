# Hermes Workshare — End-to-End Verification Guide

This verifies the complete delegation chain:
**OpenCode → MCP adapter → Hermes Runs API → Hermes Agent → results back to OpenCode**

---

## Prerequisites

- Hermes Agent installed and configured (DeepSeek V4.1 via OpenRouter)
- OpenCode 1.18.4 installed
- `hermes-workshare` plugin repo cloned at `C:\Users\i\hermes_workspaces\hermes-workshare`
- Python deps: `pip install aiohttp pydantic mcp uvicorn starlette` (in your Hermes venv or global)

---

## Step 1: Verify Hermes API Server is Running

```bash
# In terminal 1
hermes gateway run
```

Wait for:
```
[API Server] API server listening on http://127.0.0.1:8642
```

**Test it:**
```bash
curl -s http://localhost:8642/health
# → {"status":"ok","platform":"hermes-agent","version":"0.22.7"}

curl -s http://localhost:8642/v1/models -H "Authorization: Bearer change-me-local-dev"
# → {"object":"list","data":[{"id":"hermes-agent",...}]}
```

If `change-me-local-dev` doesn't work, check your `~/.hermes/.env` for `API_SERVER_KEY`.

---

## Step 2: Start MCP Adapter

```bash
# In terminal 2
cd C:\Users\i\hermes_workspaces\hermes-workshare
export HERMES_WORKSHARE_API_KEY=change-me-local-dev
export HERMES_WORKSHARE_API_URL=http://localhost:8642/v1
python scripts/mcp_server.py
```

Wait for:
```
[hermes-workshare-mcp] Starting on http://127.0.0.1:8766/mcp
[hermes-workshare-mcp] Hermes API: http://localhost:8642/v1
[hermes-workshare-mcp] API Key: SET
```

**Test it:**
```bash
# In another terminal
curl -s http://localhost:8766/mcp -H "Authorization: Bearer change-me-local-dev" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
# Should return the 6 hermes_* tools
```

---

## Step 3: Add MCP Server to OpenCode

```bash
# Global (available in all projects)
opencode mcp add hermes-workshare --global --url http://localhost:8766/mcp --header "Authorization: Bearer change-me-local-dev"

# Verify
opencode mcp list
# Should show: ✓ hermes-workshare  connected
```

**Or via config file** (`~/.config/opencode/opencode.json`):
```json
{
  "mcp": {
    "servers": {
      "hermes-workshare": {
        "type": "remote",
        "url": "http://localhost:8766/mcp",
        "headers": {
          "Authorization": "Bearer change-me-local-dev"
        },
        "codemode": false
      }
    }
  }
}
```

---

## Step 4: Test Delegation from OpenCode

### Option A: OpenCode TUI (interactive)
```bash
opencode
# In the chat, type:
# "Submit a task to Hermes: run 'echo hello from hermes' and return the output"
```

### Option B: OpenCode one-shot (easier to verify)
```bash
opencode run "Use the hermes_submit_task tool to run a simple shell command: echo 'hello from hermes workshare'"
```

**Expected flow:**
1. OpenCode calls `hermes_submit_task` → returns `run_id` immediately
2. You call `hermes_check_status` with that `run_id` → `status: running` or `completed`
3. You call `hermes_get_results` → shows output, usage, runtime

### Option C: Direct MCP tool calls (for debugging)
```bash
# Submit
curl -s http://localhost:8766/mcp -H "Authorization: Bearer change-me-local-dev" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"hermes_submit_task","arguments":{"prompt":"Run echo hello from hermes"}}}'

# Check status (use run_id from above)
curl -s http://localhost:8766/mcp -H "Authorization: Bearer change-me-local-dev" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hermes_check_status","arguments":{"run_id":"run_abc123"}}}'

# Get results
curl -s http://localhost:8766/mcp -H "Authorization: Bearer change-me-local-dev" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"hermes_get_results","arguments":{"run_id":"run_abc123"}}}'
```

---

## Step 5: Verify Advanced Features

### Steering (mid-run guidance)
```bash
# Submit a longer task
opencode run "Ask Hermes to write a Python script that counts to 10 with 1-second delays, saving each number to /tmp/count.txt"

# While it's running, steer it
opencode run "Use hermes_steer_task to tell Hermes to also print each number to stdout"
```

### Cancellation
```bash
opencode run "Ask Hermes to run an infinite loop: while true; do sleep 1; done"
# Then cancel
opencode run "Use hermes_cancel_task on that run_id"
```

### Worktree isolation
```bash
opencode run "Use hermes_submit_task with worktree set to a new directory, run 'git status' there"
```

---

## Step 6: Verify OpenCode's Own Model Still Works

```bash
opencode run "What is 2+2?"  # Should answer via DeepSeek directly, not Hermes
```

**Confirm:** OpenCode's primary model (DeepSeek) is unchanged — only explicit tool calls go to Hermes.

---

## Troubleshooting Checklist

| Symptom | Check |
|---------|-------|
| `opencode mcp list` shows `needs authentication` | MCP adapter needs `Authorization` header; verify `HERMES_WORKSHARE_API_KEY` matches `API_SERVER_KEY` |
| Tool calls return "Unknown tool" | MCP adapter not connected; check `opencode mcp list` and adapter logs |
| `hermes_submit_task` returns error | Hermes gateway not running or wrong `API_SERVER_URL`; test `curl /health` |
| Run stays `queued` forever | Concurrency limit hit; check `hermes config get platforms.api_server.max_concurrent_runs` |
| Results show `status: interrupted` | Gateway restarted or timeout; check `gateway.log` |
| OpenCode doesn't show MCP tools | Restart OpenCode after `opencode mcp add`; check `codemode: false` in config |

---

## Success Criteria

- [ ] `hermes gateway` starts and serves `/health` + `/v1/models`
- [ ] MCP adapter starts on `:8766/mcp` and lists 6 tools via `tools/list`
- [ ] `opencode mcp list` shows `hermes-workshare` connected
- [ ] OpenCode can call `hermes_submit_task` and gets a `run_id` immediately
- [ ] `hermes_check_status` returns `running` → `completed`
- [ ] `hermes_get_results` returns actual agent output, usage tokens, served runtime
- [ ] `hermes_steer_task` influences a running task
- [ ] `hermes_cancel_task` stops a run without killing gateway
- [ ] OpenCode's direct chat (no tools) still uses DeepSeek

---

## Logs to Watch

```bash
# Hermes gateway
tail -f ~/.hermes/logs/gateway.log

# MCP adapter (terminal 2 output)

# OpenCode logs (if needed)
# Usually in ~/.local/share/opencode/logs/
```

---

## Minimal Smoke Test (30 seconds)

```bash
# 1. Start gateway (if not running)
hermes gateway run &

# 2. Start MCP adapter
cd ~/hermes_workspaces/hermes-workshare
HERMES_WORKSHARE_API_KEY=change-me-local-dev python scripts/mcp_server.py &

# 3. Add to OpenCode (once)
opencode mcp add hermes-workshare --global --url http://localhost:8766/mcp --header "Authorization: Bearer change-me-local-dev"

# 4. Test
opencode run "Use hermes_submit_task to run: echo 'smoke test ok'"
# → should return run_id
opencode run "Use hermes_check_status with that run_id"
# → should show completed
opencode run "Use hermes_get_results with that run_id"
# → should show 'smoke test ok' in output
```

If all 4 steps work, the delegation chain is functional.