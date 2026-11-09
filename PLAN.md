# Hermes Workshare — proposed plugin build

Status: design for approval; implementation not yet built or tested.

## Goal
Keep OpenCode in VS Code as the primary coding agent, using its existing direct DeepSeek API connection. Let that agent hand bounded tasks to Hermes, continue independent work, inspect progress, retrieve results, and cancel delegated work. Hermes is the subordinate execution harness, not OpenCode's replacement model provider. This does not require a separate ACP chat panel.

## Package
One standalone repository/folder: hermes-workshare. A native Hermes plugin (plugin.yaml and register(ctx) entrypoint), plus a companion MCP adapter for OpenCode and other MCP clients. Do not patch Hermes internals or OpenCode source. Do not reuse the earlier unverified secondary-harness skill as implementation.

## Proposed transport
OpenCode / DeepSeek -> companion MCP adapter -> authenticated Hermes Runs API -> Hermes agent tools.

Use the documented Runs API for nonblocking task admission, lifecycle events, status, steering and cancellation. Confirm endpoint support against the installed Hermes version before coding its adapter. If the installed host lacks a required public surface, report the missing capability instead of monkey-patching core or inventing a fallback.

The native plugin supplies supported CLI setup/diagnostics and task-facing tooling where appropriate; the companion adapter exposes those capabilities to the external controller. Secrets must use supported host credential routes. Never read Hermes .env, auth.json or OpenCode credential files. Do not ship a default public password or assume a placeholder API key.

## Minimal working scope
- Submit: explicit task, context, project/worktree, acceptance criteria and idempotency identity; promptly return a task/run ID.
- Inspect: running, awaiting human approval, completed, failed, cancelled or unknown state; preserve actual host status.
- Results: worker response, available verification evidence and artifact references; never call a final message proof of successful execution.
- Cancel: interrupt only the selected delegated run, never kill a gateway or every OpenCode process.
- Continue/steer: use supported host APIs and preserve correlation between OpenCode session and Hermes run.
- Worksharing: controller keeps ownership; assign separate worktrees or non-overlapping tasks. No automatic merge, commit, push or publish.
- Small local task monitor: visible lifecycle/error history and links to results, without replacing OpenCode's coding interface. Confirm its supported plugin UI surface before implementation.
- Guardrails: no YOLO, auto-approval or permission bypass. Human approvals stay human; unattended jobs fail or wait explicitly rather than hanging invisibly. Task metadata is not a sandbox or filesystem security boundary.

## Do not change
- Existing DeepSeek credentials or primary OpenCode model/provider.
- Other plugins, MCP servers, profiles, active sessions or project code.
- Gateway lifecycle during the active conversation.

## Build stages
1. Audit installed Hermes public APIs and the installed OpenCode 1.18.4 schema. Current online OpenCode docs describe a newer V2 schema, so do not apply it blindly.
2. Write regression/contract tests for task lifecycle, errors, cancellation, idempotency, credential handling and config preservation before implementation.
3. Implement native plugin and companion adapter using supported SDKs. Pin bounded compatible dependencies.
4. Validate with hermes plugins doctor and hermes plugins validate; fix real errors and disclose scan warnings.
5. Exercise the real MCP transport and a real Hermes run in an isolated demo workspace. Demonstrate OpenCode keeping its DeepSeek provider while delegating a bounded job and consuming the result.
6. Test cancellation and connection failure without stopping the main gateway. Label any untested behavior plainly.
7. Write installation, security disclosures, uninstall/recovery instructions, sources-info.md and a demo script under 90 seconds. Prepare the catalog entry/PR description once real repository ownership and a full pinned commit SHA exist.

## Acceptance evidence
- Native plugin loads and catalog validation output is recorded.
- Actual OpenCode can discover and invoke the delegation tools without changing its primary model.
- Actual Hermes executes a delegated task and the caller retrieves its result.
- Controller remains responsive after task submission.
- Failed/blocked/cancelled runs are not presented as successful.
- Existing OpenCode configuration remains unchanged until an explicitly approved integration step; compare before/after then.
- No claims of shared chat consciousness: worker sessions are separate and receive only explicitly supplied context plus their configured Hermes context.

## Hackathon requirements from attachment / official docs
A public plugin repository; loadable plugin.yaml plus entrypoint; only public extension surfaces; truthful declared capabilities; local catalog validation; source-only reviewable payloads; security and background process disclosures; no self-updater or credential-store reads. Catalog PR must pin the full real 40-character commit SHA. Demo video under 90 seconds on X tagging @NousResearch; submit PR and video links through the supplied form. Publishing, account actions, PR creation and form submission are separate user-authorized actions, not performed by this plan.

## References
- User attachment: C:/Users/i/AppData/Local/hermes/attachments/hackaton_entry_plugin.txt
- https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
- https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission
- https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server
- https://opencode.ai/docs/mcp-servers/
