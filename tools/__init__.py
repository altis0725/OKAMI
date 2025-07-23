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

from .knowledge_search_tool import (
    search_knowledge,
    add_knowledge_to_base
)

__all__ = [
    "MCPToolWrapper",
    "create_crewai_tool",
    "get_mcp_discovery_tool",
    "get_mcp_execute_tool",
    "get_mcp_tools_for_agent",
    "search_knowledge",
    "add_knowledge_to_base"
]