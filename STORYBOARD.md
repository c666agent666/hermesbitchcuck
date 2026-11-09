# Hermes Workshare — 90-Second Demo Storyboard

**Target:** Hermes Plugin Hackathon submission video
**Format:** Screen recording + voiceover (or captions)
**Total time:** ≤ 90 seconds
**Repo:** https://github.com/c666agent666/hermesbitchcuck

---

## Scene Breakdown

| Time | Visual | Audio / Caption | Notes |
|------|--------|-----------------|-------|
| 0–3s | **Title card**: "Hermes Workshare — Delegate tasks from OpenCode to Hermes" | Music starts. Text on screen. | Repo URL in corner. |
| 3–8s | **Architecture diagram** (static slide or animated): OpenCode → MCP → Hermes API Server → Hermes Agent (tools, memory, skills) | "OpenCode stays in charge with its DeepSeek connection. Hermes runs delegated jobs as a worker." | Keep diagram simple: 3 boxes + arrows. |
| 8–15s | **Terminal**: `hermes plugins validate plugin` → "Validation passed" | "Native plugin passes catalog validation — six tools, one CLI command, no core overrides." | Show actual command output. |
| 15–22s | **Terminal**: `hermes plugins doctor plugin` → "6 tool(s) registered" | "Plugin doctor confirms runtime registration." | |
| 22–30s | **Terminal**: Start Hermes gateway (`hermes gateway`) → "API server listening on http://127.0.0.1:8642" | "Hermes API server exposes /v1/runs for async task admission." | |
| 30–38s | **Terminal**: Start MCP adapter (`python scripts/mcp_server.py`) → "Starting on http://127.0.0.1:8766/mcp" | "MCP adapter bridges OpenCode to Hermes Runs API." | |
| 38–48s | **OpenCode VS Code**: Add MCP server in settings (`opencode mcp add hermes-workshare --url http://localhost:8766/mcp`) → "Connected" | "OpenCode discovers the delegation tools via MCP." | Show `opencode mcp list` with green check. |
| 48–60s | **OpenCode chat**: User types: *"Run the test suite and summarize failures"* → Tool call: `hermes_submit_task` → Returns `run_id` immediately | "OpenCode submits a task, gets a run_id instantly — no blocking." | Highlight non-blocking return. |
| 60–70s | **OpenCode chat**: User types: *"Check status"* → Tool call: `hermes_check_status` → Shows `status: running` → User types: *"Get results"* → `hermes_get_results` → Shows test output, usage, runtime | "Poll status, retrieve results, see token usage and served model." | Show JSON response collapsing/expanding. |
| 70–78s | **OpenCode chat**: User types: *"Cancel that"* → `hermes_cancel_task` → `status: interrupted` | "Cancel any run without killing the gateway or other sessions." | |
| 78–85s | **VS Code ACP panel** (optional): Show Hermes still connected for interactive coding | "Hermes stays available for interactive ACP coding — same agent, dual role." | Quick cut, 3 seconds. |
| 85–90s | **End card**: Repo URL + "Hermes Plugin Hackathon 2026" + @NousResearch handle | Music fades. | |

---

## Recording Tips

- **Resolution**: 1920×1080 minimum
- **Terminal font**: Large enough to read (14–16pt)
- **Pacing**: Cut silence; aim for ~1.5× speaking speed
- **Zoom**: Pan/zoom on terminal output when JSON appears
- **No dead air**: Every second should show action or convey info

---

## Required Assets (prepare before recording)

- [ ] Hermes gateway running on port 8642
- [ ] MCP adapter running on port 8766
- [ ] OpenCode with MCP server added
- [ ] Test task that runs ~5–10s (e.g., `pytest -q` or `npm test`)
- [ ] Clean terminal (no prior clutter)
- [ ] Browser tab with GitHub repo open for final shot

---

## Fallback if Live Demo Fails

Pre-record each terminal step as separate clips; assemble in editor. Worst case: narrate over screenshots with cursor highlighting.