"""
OKAMI Tools
Integration with external tools and services
"""

from .mcp_tool_wrapper import (
    MCPToolWrapper,
    create_crewai_tool,
    get_mcp_discovery_tool,
    get_mcp_execute_tool,
    get_mcp_tools_for_agent,
)

from .mcp_gateway_tool import (
    MCPGatewayTool,
    MCPToolDiscoveryTool,
    DynamicMCPTool,
    create_mcp_tool,
    get_mcp_gateway_tools,
    get_common_mcp_tools,
)

from .knowledge_search_tool import (
    search_knowledge,
    add_knowledge_to_base,
)

__all__ = [
    # MCP wrapper utilities
    "MCPToolWrapper",
    "create_crewai_tool",
    "get_mcp_discovery_tool",
    "get_mcp_execute_tool",
    "get_mcp_tools_for_agent",
    # MCP gateway tools (for tests and general use)
    "MCPGatewayTool",
    "MCPToolDiscoveryTool",
    "DynamicMCPTool",
    "create_mcp_tool",
    "get_mcp_gateway_tools",
    "get_common_mcp_tools",
    # Knowledge tools
    "search_knowledge",
    "add_knowledge_to_base",
]
