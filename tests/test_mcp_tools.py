"""
Test MCP Gateway Tools
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import (
    MCPGatewayTool,
    MCPToolDiscoveryTool,
    create_mcp_tool,
    get_mcp_gateway_tools,
    get_common_mcp_tools
)


def test_mcp_gateway_tool():
    """Test basic MCP gateway tool"""
    print("Testing MCP Gateway Tool...")
    
    # Create gateway tool
    gateway = MCPGatewayTool()
    print(f"✓ Tool name: {gateway.name}")
    print(f"✓ Tool description: {gateway.description[:100]}...")
    
    # Test tool discovery
    discovery = MCPToolDiscoveryTool()
    print(f"\n✓ Discovery tool name: {discovery.name}")
    print(f"✓ Discovery tool description: {discovery.description[:100]}...")


def test_dynamic_mcp_tool():
    """Test dynamic MCP tool creation"""
    print("\n\nTesting Dynamic MCP Tool Creation...")
    
    # Create a custom MCP tool
    custom_tool = create_mcp_tool(
        "custom_api",
        "Custom API integration through MCP"
    )
    
    print(f"✓ Dynamic tool name: {custom_tool.name}")
    print(f"✓ Dynamic tool MCP name: {custom_tool._mcp_tool_name}")
    print(f"✓ Dynamic tool description: {custom_tool.description[:100]}...")


def test_common_mcp_tools():
    """Test pre-defined common MCP tools"""
    print("\n\nTesting Common MCP Tools...")
    
    common_tools = get_common_mcp_tools()
    print(f"✓ Number of common tools: {len(common_tools)}")
    
    for tool in common_tools:
        print(f"\n  - Tool: {tool.name}")
        if hasattr(tool, '_mcp_tool_name'):
            print(f"    MCP name: {tool._mcp_tool_name}")
        print(f"    Description: {tool.description[:80]}...")


def test_gateway_tools_list():
    """Test gateway tools list"""
    print("\n\nTesting Gateway Tools List...")
    
    gateway_tools = get_mcp_gateway_tools()
    print(f"✓ Number of gateway tools: {len(gateway_tools)}")
    
    for tool in gateway_tools:
        print(f"\n  - Tool: {tool.name}")
        print(f"    Type: {type(tool).__name__}")


def main():
    """Run all tests"""
    print("=== MCP Tools Test Suite ===\n")
    
    try:
        test_mcp_gateway_tool()
        test_dynamic_mcp_tool()
        test_common_mcp_tools()
        test_gateway_tools_list()
        
        print("\n\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()