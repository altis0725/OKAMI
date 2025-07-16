"""
OKAMI Tools
Integration with external tools and services
"""

from .mcp_tool_wrapper import (
    MCPToolWrapper,
    create_crewai_tool,
    get_mcp_discovery_tool,
    get_mcp_execute_tool,
    get_mcp_tools_for_agent
)

__all__ = [
    "MCPToolWrapper",
    "create_crewai_tool",
    "get_mcp_discovery_tool",
    "get_mcp_execute_tool",
    "get_mcp_tools_for_agent"
]