#!/usr/bin/env python3
"""
Hermes Workshare MCP Server

Exposes Hermes Workshare tools via MCP (Model Context Protocol) for OpenCode
and other MCP clients. Connects to the Hermes API Server's /v1/runs endpoints.

Run: python mcp_server.py
Server listens on http://127.0.0.1:8766/mcp
"""

import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp
from mcp.server import Server
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp.types import Tool, TextContent, CallToolResult
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn


# Configuration
@dataclass
class Config:
    api_server_url: str = "http://127.0.0.1:8642/v1"
    api_server_key: str = ""
    default_timeout: int = 300


CFG = Config()


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if CFG.api_server_key:
        h["Authorization"] = f"Bearer {CFG.api_server_key}"
    return h


# Request models
class SubmitTaskArgs(BaseModel):
    prompt: str = Field(..., description="Task description for Hermes to execute")
    context: str = Field(default="", description="Optional context to prepend")
    worktree: str = Field(default="", description="Worktree path (optional)")
    acceptance_criteria: str = Field(default="", description="Explicit completion criteria")
    idempotency_key: str = Field(default="", description="Optional idempotency key")
    timeout_seconds: int = Field(default=0, description="Override default timeout (0 = use default)")


class CheckStatusArgs(BaseModel):
    run_id: str = Field(..., description="Run ID returned from submit_task")


class GetResultsArgs(BaseModel):
    run_id: str = Field(..., description="Run ID returned from submit_task")


class SteerTaskArgs(BaseModel):
    run_id: str = Field(..., description="Run ID to steer")
    guidance: str = Field(..., description="Mid-run guidance to send")


class CancelTaskArgs(BaseModel):
    run_id: str = Field(..., description="Run ID to cancel")


class ConfigureArgs(BaseModel):
    api_server_url: str | None = Field(default=None, description="API server base URL")
    api_server_key: str | None = Field(default=None, description="API server bearer token")
    default_worktree: str | None = Field(default=None, description="Default worktree path")
    default_timeout_seconds: int | None = Field(default=None, description="Default timeout in seconds")


server = Server("hermes-workshare-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="hermes_submit_task",
            description="Submit a task to Hermes for async execution. Returns run_id immediately.",
            inputSchema=SubmitTaskArgs.model_json_schema(),
        ),
        Tool(
            name="hermes_check_status",
            description="Check the current status of a delegated run.",
            inputSchema=CheckStatusArgs.model_json_schema(),
        ),
        Tool(
            name="hermes_get_results",
            description="Retrieve the final results of a completed run.",
            inputSchema=GetResultsArgs.model_json_schema(),
        ),
        Tool(
            name="hermes_steer_task",
            description="Send mid-run guidance to a running task.",
            inputSchema=SteerTaskArgs.model_json_schema(),
        ),
        Tool(
            name="hermes_cancel_task",
            description="Cancel a running task.",
            inputSchema=CancelTaskArgs.model_json_schema(),
        ),
        Tool(
            name="hermes_configure",
            description="View or update MCP server configuration.",
            inputSchema=ConfigureArgs.model_json_schema(),
        ),
    ]


async def _post(path: str, data: dict, timeout: int | None = None) -> dict:
    url = f"{CFG.api_server_url.rstrip('/')}{path}"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json=data, headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=timeout or CFG.default_timeout)
        ) as resp:
            return await resp.json()


async def _get(path: str) -> dict:
    url = f"{CFG.api_server_url.rstrip('/')}{path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=_headers(), timeout=aiohttp.ClientTimeout(total=30)) as resp:
            return await resp.json()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    if not CFG.api_server_key:
        return CallToolResult(
            content=[TextContent(type="text", text="ERROR: API server key not configured. Set HERMES_WORKSHARE_API_KEY env var.")]
        )

    try:
        if name == "hermes_submit_task":
            args = SubmitTaskArgs(**arguments)
            payload = {"input": args.prompt}
            if args.context:
                payload["instructions"] = args.context
            if args.worktree:
                payload["session_id"] = args.worktree
            if args.acceptance_criteria:
                payload.setdefault("metadata", {})["acceptance_criteria"] = args.acceptance_criteria

            headers = _headers()
            if args.idempotency_key:
                headers["Idempotency-Key"] = args.idempotency_key

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{CFG.api_server_url.rstrip('/')}/runs",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=args.timeout_seconds or CFG.default_timeout),
                ) as resp:
                    data = await resp.json()
                    if resp.status >= 400:
                        return CallToolResult(content=[TextContent(type="text", text=f"ERROR {resp.status}: {data.get('error', 'Unknown error')}")])
                    return CallToolResult(content=[TextContent(type="text", text=json.dumps(data, indent=2))])

        elif name == "hermes_check_status":
            args = CheckStatusArgs(**arguments)
            data = await _get(f"/runs/{args.run_id}")
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(data, indent=2))])

        elif name == "hermes_get_results":
            args = GetResultsArgs(**arguments)
            data = await _get(f"/runs/{args.run_id}")
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(data, indent=2))])

        elif name == "hermes_steer_task":
            args = SteerTaskArgs(**arguments)
            data = await _post(f"/runs/{args.run_id}/steer", {"guidance": args.guidance})
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(data, indent=2))])

        elif name == "hermes_cancel_task":
            args = CancelTaskArgs(**arguments)
            data = await _post(f"/runs/{args.run_id}/stop", {})
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(data, indent=2))])

        elif name == "hermes_configure":
            args = ConfigureArgs(**arguments)
            if args.api_server_url is not None:
                CFG.api_server_url = args.api_server_url
            if args.api_server_key is not None:
                CFG.api_server_key = args.api_server_key
            if args.default_worktree is not None:
                CFG.default_timeout = args.default_timeout_seconds
            return CallToolResult(content=[TextContent(type="text", text=json.dumps({
                "api_server_url": CFG.api_server_url,
                "has_api_key": bool(CFG.api_server_key),
                "default_timeout": CFG.default_timeout,
            }, indent=2))])

        else:
            return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")])

    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"ERROR: {str(e)}")])


async def main():
    # Load config from environment
    CFG.api_server_url = os.environ.get("HERMES_WORKSHARE_API_URL", CFG.api_server_url)
    CFG.api_server_key = os.environ.get("HERMES_WORKSHARE_API_KEY", CFG.api_server_key)
    CFG.default_timeout = int(os.environ.get("HERMES_WORKSHARE_TIMEOUT", str(CFG.default_timeout)))

    transport = StreamableHTTPServerTransport(server, path="/mcp")

    async def handle_scope(scope, receive, send):
        await transport.handle_scope(scope, receive, send)

    app = Starlette(routes=[Mount("/mcp", app=handle_scope)])
    config = uvicorn.Config(app, host="127.0.0.1", port=8766, log_level="info")
    srv = uvicorn.Server(config)
    print(f"[hermes-workshare-mcp] Starting on http://127.0.0.1:8766/mcp")
    print(f"[hermes-workshare-mcp] Hermes API: {CFG.api_server_url}")
    print(f"[hermes-workshare-mcp] API Key: {'SET' if CFG.api_server_key else 'NOT SET'}")
    await srv.serve()


if __name__ == "__main__":
    asyncio.run(main())