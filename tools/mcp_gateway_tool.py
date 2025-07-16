"""
MCP Gateway Tool for OKAMI
Enables dynamic access to various MCP tools through Docker MCP toolkit
"""

import subprocess
import json
from typing import Dict, Any, List, Optional, Union
from crewai.tools import BaseTool
import structlog

logger = structlog.get_logger()


class MCPGatewayTool(BaseTool):
    """Tool for accessing various MCP tools through Docker MCP Gateway"""
    
    name: str = "mcp_gateway"
    description: str = """
    Access various MCP tools through the Docker MCP Gateway.
    This tool allows dynamic interaction with multiple MCP services including:
    - File system operations
    - Web browsing and search
    - Database connections
    - API integrations
    - And many other MCP-enabled tools
    
    Usage: Provide the MCP tool name and parameters to execute.
    """
    
    def _run(self, tool_name: str, action: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute an MCP tool command through the gateway
        
        Args:
            tool_name: Name of the MCP tool to use (e.g., 'filesystem', 'browser', 'github')
            action: The action to perform with the tool
            params: Optional parameters for the action
            
        Returns:
            Tool execution result or error message
        """
        try:
            # Build the MCP command
            if params:
                params_json = json.dumps(params)
                command = f"docker mcp gateway run --tool {tool_name} --action {action} --params '{params_json}'"
            else:
                command = f"docker mcp gateway run --tool {tool_name} --action {action}"
            
            logger.info(
                "Executing MCP tool",
                tool=tool_name,
                action=action,
                has_params=bool(params)
            )
            
            # Execute the command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(
                    "MCP tool execution successful",
                    tool=tool_name,
                    action=action
                )
                return result.stdout
            else:
                logger.error(
                    "MCP tool execution failed",
                    tool=tool_name,
                    action=action,
                    error=result.stderr
                )
                return f"Error executing {tool_name}.{action}: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            logger.error(
                "MCP tool execution timed out",
                tool=tool_name,
                action=action
            )
            return f"Error: {tool_name}.{action} timed out after 60 seconds"
        except Exception as e:
            logger.error(
                "MCP tool execution error",
                tool=tool_name,
                action=action,
                error=str(e)
            )
            return f"Error executing {tool_name}.{action}: {str(e)}"


class MCPToolDiscoveryTool(BaseTool):
    """Tool for discovering available MCP tools"""
    
    name: str = "mcp_discover_tools"
    description: str = """
    Discover available MCP tools and their capabilities.
    Lists all tools accessible through the MCP gateway and their available actions.
    """
    
    def _run(self) -> str:
        """Discover available MCP tools"""
        try:
            command = "docker mcp gateway list-tools"
            
            logger.info("Discovering MCP tools")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("MCP tool discovery successful")
                return result.stdout
            else:
                logger.error(
                    "MCP tool discovery failed",
                    error=result.stderr
                )
                return f"Error discovering tools: {result.stderr}"
                
        except Exception as e:
            logger.error(
                "MCP tool discovery error",
                error=str(e)
            )
            return f"Error discovering tools: {str(e)}"


class DynamicMCPTool(BaseTool):
    """Dynamic tool that adapts to any MCP tool"""
    
    name: str = "dynamic_mcp_tool"
    description: str = "Dynamic MCP tool adapter"
    
    def __init__(self, tool_name: str, tool_description: str = None):
        """
        Initialize dynamic MCP tool
        
        Args:
            tool_name: Name of the MCP tool
            tool_description: Optional description of the tool
        """
        # Set attributes before calling super().__init__()
        self.name = f"mcp_{tool_name}"
        self.description = tool_description or f"""
        Access the {tool_name} MCP tool.
        This tool provides dynamic access to {tool_name} functionality through MCP.
        """
        super().__init__()
        # Store tool name after initialization
        self._mcp_tool_name = tool_name
    
    def _run(self, action: str, **kwargs) -> str:
        """
        Execute an action on the MCP tool
        
        Args:
            action: The action to perform
            **kwargs: Additional parameters for the action
            
        Returns:
            Execution result
        """
        gateway = MCPGatewayTool()
        return gateway._run(
            tool_name=self._mcp_tool_name,
            action=action,
            params=kwargs if kwargs else None
        )


def create_mcp_tool(tool_name: str, description: str = None) -> DynamicMCPTool:
    """
    Factory function to create MCP tools dynamically
    
    Args:
        tool_name: Name of the MCP tool
        description: Optional tool description
        
    Returns:
        DynamicMCPTool instance
    """
    return DynamicMCPTool(tool_name, description)


def get_mcp_gateway_tools() -> List[BaseTool]:
    """Get core MCP gateway tools"""
    return [
        MCPGatewayTool(),
        MCPToolDiscoveryTool()
    ]


# Pre-defined common MCP tools
class MCPFileSystemTool(DynamicMCPTool):
    """MCP FileSystem tool for file operations"""
    def __init__(self):
        super().__init__(
            "filesystem",
            "Perform file system operations including read, write, list, and search files"
        )


class MCPBrowserTool(DynamicMCPTool):
    """MCP Browser tool for web interactions"""
    def __init__(self):
        super().__init__(
            "browser",
            "Browse websites, search the web, and extract information from web pages"
        )


class MCPGitHubTool(DynamicMCPTool):
    """MCP GitHub tool for repository operations"""
    def __init__(self):
        super().__init__(
            "github",
            "Interact with GitHub repositories, issues, pull requests, and more"
        )


class MCPDatabaseTool(DynamicMCPTool):
    """MCP Database tool for database operations"""
    def __init__(self):
        super().__init__(
            "database",
            "Connect to and query various databases through MCP"
        )


def get_common_mcp_tools() -> List[BaseTool]:
    """Get commonly used pre-defined MCP tools"""
    return [
        MCPFileSystemTool(),
        MCPBrowserTool(),
        MCPGitHubTool(),
        MCPDatabaseTool()
    ]