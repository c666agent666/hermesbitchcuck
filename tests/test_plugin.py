#!/usr/bin/env python3
"""Test suite for Hermes Workshare plugin and MCP adapter."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add plugin to path
PLUGIN_DIR = Path(__file__).parent.parent / "plugin"
sys.path.insert(0, str(PLUGIN_DIR))

# Import the plugin module
import __init__ as plugin_module


class MockPluginContext:
    """Mock Hermes plugin context for testing."""
    def __init__(self):
        self.config = {"hermes-workshare": {}}
        self.tools = {}
        self.cli_commands = {}
        self.declared_caps = {}

    def register_tool(self, name, toolset, description, schema, handler):
        self.tools[name] = handler
        print(f"  Registered tool: {name} (toolset: {toolset})")

    def register_cli_command(self, name, help, setup_fn, handler_fn):
        self.cli_commands[name] = {"help": help, "setup_fn": setup_fn, "handler_fn": handler_fn}
        print(f"  Registered CLI: {name}")

    def declare_capabilities(self, **kwargs):
        self.declared_caps = kwargs
        print(f"  Declared capabilities: {list(kwargs.keys())}")


def test_plugin_registration():
    """Test that plugin registers all expected tools and CLI."""
    ctx = MockPluginContext()
    plugin_module.register(ctx)

    expected_tools = {
        "hermes_workshare_submit_task",
        "hermes_workshare_check_status",
        "hermes_workshare_get_results",
        "hermes_workshare_steer_task",
        "hermes_workshare_cancel_task",
        "hermes_workshare_configure",
    }
    assert expected_tools.issubset(ctx.tools.keys()), f"Missing tools: {expected_tools - ctx.tools.keys()}"

    assert "workshare" in ctx.cli_commands
    assert "setup_fn" in ctx.cli_commands["workshare"]
    assert "handler_fn" in ctx.cli_commands["workshare"]

    assert "tools" in ctx.declared_caps
    assert expected_tools.issubset(set(ctx.declared_caps["tools"]))
    print("✓ Plugin registration test passed")


def test_config_defaults():
    """Test config loading with defaults."""
    ctx = MockPluginContext()
    plugin_module.register(ctx)

    # Call configure with no args to see defaults
    import asyncio
    result = asyncio.run(ctx.tools["hermes_workshare_configure"]())
    assert result["api_server_url"] == "http://127.0.0.1:8642/v1"
    assert result["has_api_key"] is False
    assert result["default_worktree"] == ""
    assert result["default_timeout_seconds"] == 300
    print("✓ Config defaults test passed")


def test_cli_configure():
    """Test CLI configure command via handler."""
    ctx = MockPluginContext()
    plugin_module.register(ctx)

    # Test configure via handler_fn
    import argparse
    parser = argparse.ArgumentParser()
    ctx.cli_commands["workshare"]["setup_fn"](parser)
    args = parser.parse_args(["configure", "--url", "http://localhost:9999/v1", "--worktree", "/tmp/test", "--timeout", "600"])
    handler_fn = ctx.cli_commands["workshare"]["handler_fn"]
    result = handler_fn(args)
    assert result == 0

    # Verify config was updated
    import asyncio
    cfg_result = asyncio.run(ctx.tools["hermes_workshare_configure"]())
    assert cfg_result["api_server_url"] == "http://localhost:9999/v1"
    assert cfg_result["default_worktree"] == "/tmp/test"
    assert cfg_result["default_timeout_seconds"] == 600
    print("✓ CLI configure test passed")


def test_mcp_server_imports():
    """Test that MCP server script can be imported without errors."""
    script_path = Path(__file__).parent.parent / "scripts" / "mcp_server.py"
    # Just verify syntax by compiling
    with open(script_path) as f:
        code = f.read()
    compile(code, str(script_path), 'exec')
    print("✓ MCP server syntax test passed")


def test_plugin_yaml():
    """Test plugin.yaml is valid YAML."""
    import yaml
    yaml_path = Path(__file__).parent.parent / "plugin" / "plugin.yaml"
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    assert data["name"] == "hermes-workshare"
    assert "provides_tools" in data
    assert "hermes_workshare_submit_task" in data["provides_tools"]
    print("✓ plugin.yaml validation passed")


def test_mcp_config():
    """Test MCP server config is valid JSON."""
    config_path = Path(__file__).parent.parent / "mcp_server_config.json"
    with open(config_path) as f:
        data = json.load(f)

    assert data["name"] == "hermes-workshare"
    assert data["type"] == "remote"
    assert "url" in data
    print("✓ MCP config validation passed")


if __name__ == "__main__":
    print("Running Hermes Workshare tests...\n")

    test_plugin_registration()
    test_config_defaults()
    test_cli_configure()
    test_mcp_server_imports()
    test_plugin_yaml()
    test_mcp_config()

    print("\n✓ All tests passed!")
