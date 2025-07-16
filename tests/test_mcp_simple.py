"""
Test simple MCP tools
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import get_mcp_discovery_tool, get_mcp_execute_tool, get_mcp_tools_for_agent


def test_mcp_tools():
    """Test MCP tools"""
    print("Testing MCP Tools...")
    
    # Get the tools
    discover_tool = get_mcp_discovery_tool()
    execute_tool = get_mcp_execute_tool()
    
    print(f"\n✓ Discovery tool name: {discover_tool.__name__}")
    print(f"  Description: {discover_tool.__doc__}")
    
    print(f"\n✓ Execute tool name: {execute_tool.__name__}")
    print(f"  Description: {execute_tool.__doc__}")
    
    # Test get all tools
    all_tools = get_mcp_tools_for_agent()
    print(f"\n✓ Total MCP tools: {len(all_tools)}")
    for tool in all_tools:
        print(f"  - {tool.__name__}")


def test_tool_signatures():
    """Test tool function signatures"""
    print("\n\nTesting Tool Signatures...")
    
    execute_tool = get_mcp_execute_tool()
    
    # Test calling signature
    import inspect
    sig = inspect.signature(execute_tool)
    print(f"\n✓ Execute tool signature: {sig}")
    
    # Show parameters
    for param_name, param in sig.parameters.items():
        print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'}")


def main():
    """Run tests"""
    print("=== Simple MCP Tools Test ===\n")
    
    try:
        test_mcp_tools()
        test_tool_signatures()
        
        print("\n\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()