"""
MCP Tool Wrapper for OKAMI
Provides a wrapper approach for MCP tools to avoid Pydantic conflicts
"""

import subprocess
import json
from typing import Dict, Any, List, Optional, Callable


class MCPToolWrapper:
    """Wrapper for MCP tools that works with CrewAI"""
    
    def __init__(self, tool_name: str, description: str = None):
        """
        Initialize MCP tool wrapper
        
        Args:
            tool_name: Name of the MCP tool
            description: Optional description
        """
        self.tool_name = tool_name
        self.description = description or f"Access {tool_name} through MCP gateway"
        self.name = f"mcp_{tool_name}"
    
    def __call__(self, action: str, **params) -> str:
        """
        Make the wrapper callable like a tool
        
        Args:
            action: The action to perform
            **params: Parameters for the action
            
        Returns:
            Execution result
        """
        return self.execute(action, params)
    
    def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute an MCP tool command
        
        Args:
            action: The action to perform
            params: Optional parameters
            
        Returns:
            Execution result
        """
        try:
            # Build the MCP command
            if params:
                params_json = json.dumps(params)
                command = f"docker mcp gateway run --tool {self.tool_name} --action {action} --params '{params_json}'"
            else:
                command = f"docker mcp gateway run --tool {self.tool_name} --action {action}"
            
            # Execute the command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return f"Error: Timeout executing {self.tool_name}.{action}"
        except Exception as e:
            return f"Error: {str(e)}"


def create_crewai_tool(wrapper: MCPToolWrapper) -> Callable:
    """
    Create a function that CrewAI can use as a tool
    
    Args:
        wrapper: MCPToolWrapper instance
        
    Returns:
        Callable function for CrewAI
    """
    def tool_function(action: str, **params) -> str:
        """
        Execute MCP tool action
        
        Args:
            action: The action to perform
            **params: Parameters for the action
            
        Returns:
            Execution result
        """
        return wrapper.execute(action, params)
    
    # Set function attributes that CrewAI expects
    tool_function.__name__ = wrapper.name
    tool_function.__doc__ = wrapper.description
    
    return tool_function


# Core MCP tools
def get_mcp_discovery_tool() -> Callable:
    """Get MCP discovery tool"""
    def discover_tools() -> str:
        """
        Discover available MCP tools
        
        Returns:
            List of available tools
        """
        try:
            result = subprocess.run(
                "docker mcp gateway list-tools",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error discovering tools: {result.stderr}"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    discover_tools.__name__ = "mcp_discover"
    discover_tools.__doc__ = "Discover available MCP tools and their capabilities"
    
    return discover_tools


def get_mcp_execute_tool() -> Callable:
    """Get MCP execution tool"""
    def execute_mcp_tool(tool_name: str, action: str, **params) -> str:
        """
        Execute any discovered MCP tool
        
        Args:
            tool_name: Name of the MCP tool
            action: Action to perform
            **params: Parameters for the action
            
        Returns:
            Execution result
        """
        wrapper = MCPToolWrapper(tool_name)
        return wrapper.execute(action, params)
    
    execute_mcp_tool.__name__ = "mcp_execute"
    execute_mcp_tool.__doc__ = "Execute any discovered MCP tool with specified action and parameters"
    
    return execute_mcp_tool


def get_mcp_tools_for_agent() -> List[Callable]:
    """Get core MCP tools for CrewAI agents"""
    return [
        get_mcp_discovery_tool(),
        get_mcp_execute_tool()
    ]