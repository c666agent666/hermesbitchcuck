# Hermes Workshare

A proposed Hermes Agent plugin for delegating work from OpenCode without replacing OpenCode's model provider.

**Status: design stage. No working plugin implementation is included yet.**

## Intended workflow

```text
User -> OpenCode in VS Code -> existing DeepSeek connection
             |
             +-> delegate selected tasks -> Hermes worker
             <- progress, results, follow-up and cancellation
```

OpenCode remains the controller. Hermes runs delegated jobs using its agent tools. The integration is intended to use a native Hermes plugin and a companion MCP adapter, with asynchronous task IDs instead of blocking the controller for the duration of a job.

## Planned capabilities

- Submit bounded tasks with context and acceptance criteria.
- Inspect actual run state and retrieve results.
- Steer or cancel individual delegated jobs.
- Preserve human approval boundaries.
- Separate work to reduce conflicting file edits.
- Keep existing OpenCode credentials and provider configuration unchanged.

See [PLAN.md](PLAN.md) for the proposed architecture, build stages, acceptance criteria and hackathon requirements.

## Verification status

Implementation, plugin validation, real OpenCode-to-Hermes delegation tests and demo recording are pending. This repository is not currently installable as a Hermes plugin.

## References

- [Hermes plugin developer guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
- [Plugin catalog submission](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission)
- [Hermes Runs API](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server)

No API keys, credential stores or active application configurations are included.
