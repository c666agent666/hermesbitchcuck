"""Hermes Workshare Plugin — native Hermes plugin for agent-to-agent task delegation.

This plugin provides tools that allow external agents (via MCP adapter) to submit
tasks to Hermes, check status, retrieve results, steer, and cancel delegated work.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp
from pydantic import BaseModel, Field


# Configuration model
@dataclass
class WorkshareConfig:
    api_server_url: str = "http://127.0.0.1:8642/v1"
    api_server_key: str = ""
    default_worktree: str = ""
    default_timeout_seconds: int = 300


# Request/Response models
class SubmitTaskRequest(BaseModel):
    prompt: str = Field(..., description="Task description for Hermes to execute")
    context: str = Field(default="", description="Optional context to prepend")
    worktree: str = Field(default="", description="Worktree path (optional)")
    acceptance_criteria: str = Field(default="", description="Explicit completion criteria")
    idempotency_key: str = Field(default="", description="Optional idempotency key")
    timeout_seconds: int = Field(default=0, description="Override default timeout (0 = use default)")


class SubmitTaskResponse(BaseModel):
    run_id: str
    status: str
    message: str


class RunStatus(BaseModel):
    run_id: str
    status: str
    created_at: float
    updated_at: float
    session_id: str | None = None
    model: str | None = None
    last_event: str | None = None
    error: str | None = None


class RunResults(BaseModel):
    run_id: str
    status: str
    output: str | None = None
    error: str | None = None
    usage: dict | None = None
    runtime: dict | None = None


class SteerTaskRequest(BaseModel):
    run_id: str
    guidance: str


class CancelTaskRequest(BaseModel):
    run_id: str


class ConfigureRequest(BaseModel):
    api_server_url: str | None = None
    api_server_key: str | None = None
    default_worktree: str | None = None
    default_timeout_seconds: int | None = None


class ConfigureResponse(BaseModel):
    api_server_url: str
    has_api_key: bool
    default_worktree: str
    default_timeout_seconds: int


# Global config instance
_config = WorkshareConfig()


def _get_config(ctx: Any) -> WorkshareConfig:
    """Get config from plugin config or environment."""
    global _config
    # Try to read from plugin config if available
    try:
        plugin_config = ctx.config.get("hermes-workshare", {})
        if plugin_config:
            _config.api_server_url = plugin_config.get("api_server_url", _config.api_server_url)
            _config.api_server_key = plugin_config.get("api_server_key", _config.api_server_key)
            _config.default_worktree = plugin_config.get("default_worktree", _config.default_worktree)
            _config.default_timeout_seconds = plugin_config.get("default_timeout_seconds", _config.default_timeout_seconds)
    except Exception:
        pass
    # Environment overrides
    _config.api_server_url = os.environ.get("HERMES_WORKSHARE_API_URL", _config.api_server_url)
    _config.api_server_key = os.environ.get("HERMES_WORKSHARE_API_KEY", _config.api_server_key)
    _config.default_worktree = os.environ.get("HERMES_WORKSHARE_WORKTREE", _config.default_worktree)
    return _config


def _headers(cfg: WorkshareConfig) -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if cfg.api_server_key:
        h["Authorization"] = f"Bearer {cfg.api_server_key}"
    return h


async def _post_json(cfg: WorkshareConfig, path: str, data: dict) -> dict:
    url = f"{cfg.api_server_url.rstrip('/')}{path}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=_headers(cfg), timeout=aiohttp.ClientTimeout(total=30)) as resp:
            return await resp.json()


async def _get_json(cfg: WorkshareConfig, path: str) -> dict:
    url = f"{cfg.api_server_url.rstrip('/')}{path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=_headers(cfg), timeout=aiohttp.ClientTimeout(total=30)) as resp:
            return await resp.json()


def register(ctx: Any) -> None:
    """Register Hermes Workshare tools with the Hermes agent."""

    # Submit a task to Hermes
    async def submit_task(
        prompt: str,
        context: str = "",
        worktree: str = "",
        acceptance_criteria: str = "",
        idempotency_key: str = "",
        timeout_seconds: int = 0,
    ) -> dict[str, Any]:
        """Submit a task to Hermes for execution. Returns a run_id immediately."""
        cfg = _get_config(ctx)
        if not cfg.api_server_key:
            return {"error": "API server key not configured. Set HERMES_WORKSHARE_API_KEY or configure plugin."}

        payload = {
            "input": prompt,
            "session_id": worktree or cfg.default_worktree or None,
        }
        if context:
            payload["instructions"] = context
        if acceptance_criteria:
            payload.setdefault("metadata", {})["acceptance_criteria"] = acceptance_criteria

        headers = _headers(cfg)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{cfg.api_server_url.rstrip('/')}/runs",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout_seconds or cfg.default_timeout_seconds),
                ) as resp:
                    data = await resp.json()
                    if resp.status >= 400:
                        return {"error": data.get("error", "Unknown error"), "status_code": resp.status}
                    return {"run_id": data.get("run_id"), "status": data.get("status", "accepted")}
        except Exception as e:
            return {"error": str(e)}

    # Check run status
    async def check_status(run_id: str) -> dict[str, Any]:
        """Get the current status of a delegated run."""
        cfg = _get_config(ctx)
        if not cfg.api_server_key:
            return {"error": "API server key not configured."}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{cfg.api_server_url.rstrip('/')}/runs/{run_id}",
                    headers=_headers(cfg),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()
                    if resp.status >= 400:
                        return {"error": data.get("error", "Unknown error"), "status_code": resp.status}
                    return data
        except Exception as e:
            return {"error": str(e)}

    # Get run results
    async def get_results(run_id: str) -> dict[str, Any]:
        """Retrieve the final results of a completed run."""
        cfg = _get_config(ctx)
        if not cfg.api_server_key:
            return {"error": "API server key not configured."}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{cfg.api_server_url.rstrip('/')}/runs/{run_id}",
                    headers=_headers(cfg),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()
                    if resp.status >= 400:
                        return {"error": data.get("error", "Unknown error"), "status_code": resp.status}
                    # The status endpoint returns full run info including output
                    return data
        except Exception as e:
            return {"error": str(e)}

    # Steer a running task
    async def steer_task(run_id: str, guidance: str) -> dict[str, Any]:
        """Send mid-run guidance to a running task."""
        cfg = _get_config(ctx)
        if not cfg.api_server_key:
            return {"error": "API server key not configured."}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{cfg.api_server_url.rstrip('/')}/runs/{run_id}/steer",
                    json={"guidance": guidance},
                    headers=_headers(cfg),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()
                    if resp.status >= 400:
                        return {"error": data.get("error", "Unknown error"), "status_code": resp.status}
                    return data
        except Exception as e:
            return {"error": str(e)}

    # Cancel a running task
    async def cancel_task(run_id: str) -> dict[str, Any]:
        """Cancel a running task."""
        cfg = _get_config(ctx)
        if not cfg.api_server_key:
            return {"error": "API server key not configured."}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{cfg.api_server_url.rstrip('/')}/runs/{run_id}/stop",
                    json={},
                    headers=_headers(cfg),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()
                    if resp.status >= 400:
                        return {"error": data.get("error", "Unknown error"), "status_code": resp.status}
                    return data
        except Exception as e:
            return {"error": str(e)}

    # Configure the plugin
    async def configure(
        api_server_url: str | None = None,
        api_server_key: str | None = None,
        default_worktree: str | None = None,
        default_timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """View or update plugin configuration."""
        cfg = _get_config(ctx)

        if api_server_url is not None:
            cfg.api_server_url = api_server_url
        if api_server_key is not None:
            cfg.api_server_key = api_server_key
        if default_worktree is not None:
            cfg.default_worktree = default_worktree
        if default_timeout_seconds is not None:
            cfg.default_timeout_seconds = default_timeout_seconds

        return {
            "api_server_url": cfg.api_server_url,
            "has_api_key": bool(cfg.api_server_key),
            "default_worktree": cfg.default_worktree,
            "default_timeout_seconds": cfg.default_timeout_seconds,
        }

    # Register all tools
    ctx.register_tool(
        name="hermes_workshare_submit_task",
        toolset="hermes_workshare",
        description="Submit a task to Hermes for execution. Returns a run_id immediately.",
        schema=SubmitTaskRequest.model_json_schema(),
        handler=submit_task,
    )

    ctx.register_tool(
        name="hermes_workshare_check_status",
        toolset="hermes_workshare",
        description="Get the current status of a delegated run.",
        schema={"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"]},
        handler=check_status,
    )

    ctx.register_tool(
        name="hermes_workshare_get_results",
        toolset="hermes_workshare",
        description="Retrieve the final results of a completed run.",
        schema={"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"]},
        handler=get_results,
    )

    ctx.register_tool(
        name="hermes_workshare_steer_task",
        toolset="hermes_workshare",
        description="Send mid-run guidance to a running task.",
        schema={"type": "object", "properties": {"run_id": {"type": "string"}, "guidance": {"type": "string"}}, "required": ["run_id", "guidance"]},
        handler=steer_task,
    )

    ctx.register_tool(
        name="hermes_workshare_cancel_task",
        toolset="hermes_workshare",
        description="Cancel a running task.",
        schema={"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"]},
        handler=cancel_task,
    )

    ctx.register_tool(
        name="hermes_workshare_configure",
        toolset="hermes_workshare",
        description="View or update plugin configuration (API URL, key, defaults).",
        schema=ConfigureRequest.model_json_schema(),
        handler=configure,
    )

    # Register CLI command for diagnostics
    def cli_configure(args: list[str]) -> int:
        """CLI: hermes workshare configure [--url URL] [--key KEY] [--worktree PATH] [--timeout SECS]"""
        import argparse
        parser = argparse.ArgumentParser(prog="hermes workshare configure")
        parser.add_argument("--url", help="API server base URL")
        parser.add_argument("--key", help="API server bearer token")
        parser.add_argument("--worktree", help="Default worktree path")
        parser.add_argument("--timeout", type=int, help="Default timeout seconds")
        parsed = parser.parse_args(args)

        cfg = _get_config(ctx)
        if parsed.url:
            cfg.api_server_url = parsed.url
        if parsed.key:
            cfg.api_server_key = parsed.key
        if parsed.worktree:
            cfg.default_worktree = parsed.worktree
        if parsed.timeout:
            cfg.default_timeout_seconds = parsed.timeout

        print(f"API URL: {cfg.api_server_url}")
        print(f"API Key: {'SET' if cfg.api_server_key else 'NOT SET'}")
        print(f"Worktree: {cfg.default_worktree or '(none)'}")
        print(f"Timeout: {cfg.default_timeout_seconds}s")
        return 0

    def cli_test(args: list[str]) -> int:
        """CLI: hermes workshare test -- quick connectivity check."""
        cfg = _get_config(ctx)
        if not cfg.api_server_key:
            print("ERROR: API server key not configured")
            return 1

        async def _test():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{cfg.api_server_url.rstrip('/')}/health",
                        headers=_headers(cfg),
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            print(f"OK: {data}")
                            return 0
                        else:
                            print(f"FAIL: HTTP {resp.status}")
                            return 1
            except Exception as e:
                print(f"ERROR: {e}")
                return 1

        return asyncio.run(_test())

    def _cli_setup(subparser):
        subparser.add_argument("action", choices=["configure", "test"], help="Action to perform")
        subparser.add_argument("--url", help="API server base URL")
        subparser.add_argument("--key", help="API server bearer token")
        subparser.add_argument("--worktree", help="Default worktree path")
        subparser.add_argument("--timeout", type=int, help="Default timeout seconds")

    def _cli_handler(args):
        if args.action == "configure":
            return cli_configure([
                "--url", args.url or "",
                "--worktree", args.worktree or "",
                "--timeout", str(args.timeout or ""),
            ])
        elif args.action == "test":
            return cli_test([])
        return 0

    ctx.register_cli_command(
        name="workshare",
        help="Hermes Workshare: configure and test delegation to Hermes",
        setup_fn=_cli_setup,
        handler_fn=_cli_handler,
    )

    # Declare capabilities
    if hasattr(ctx, "declare_capabilities"):
        ctx.declare_capabilities(
            tools=[
                "hermes_workshare_submit_task",
                "hermes_workshare_check_status",
                "hermes_workshare_get_results",
                "hermes_workshare_steer_task",
                "hermes_workshare_cancel_task",
                "hermes_workshare_configure",
            ],
            cli_commands=["workshare"],
            config_schema={
                "api_server_url": {"type": "string", "default": "http://127.0.0.1:8642/v1"},
                "api_server_key": {"type": "string", "secret": True},
                "default_worktree": {"type": "string", "default": ""},
                "default_timeout_seconds": {"type": "integer", "default": 300},
            },
            environment=[],
        )

    print("[hermes-workshare] Plugin loaded: submit_task, check_status, get_results, steer_task, cancel_task, configure")


# For direct testing
if __name__ == "__main__":
    class MockCtx:
        def __init__(self):
            self.config = {"hermes-workshare": {}}
            self.tools = {}
            self.cli_commands = {}

        def register_tool(self, name, description, parameters, handler):
            self.tools[name] = handler
            print(f"Registered tool: {name}")

        def register_cli_command(self, name, description, subcommands):
            self.cli_commands[name] = subcommands
            print(f"Registered CLI: {name}")

        def declare_capabilities(self, **kwargs):
            print(f"Declared capabilities: {list(kwargs.keys())}")

        def config_get(self, key, default=None):
            return self.config.get(key, default)

    import asyncio
    ctx = MockCtx()
    register(ctx)
    print("\nPlugin registration test passed.")