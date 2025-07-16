"""
Docker MCP Toolkit Integration for OKAMI
Connects to Docker MCP Gateway for container management
"""

import subprocess
import json
from typing import Dict, Any, List, Optional
from crewai.tools import BaseTool
import structlog

logger = structlog.get_logger()


class DockerMCPTool(BaseTool):
    """Tool for interacting with Docker through MCP Gateway"""
    
    name: str = "docker_mcp"
    description: str = """
    Interact with Docker containers through MCP Gateway.
    Capabilities:
    - List containers
    - Start/stop containers
    - View container logs
    - Execute commands in containers
    - Manage images
    """
    
    def _run(self, command: str) -> str:
        """
        Execute Docker MCP command
        
        Args:
            command: Docker command to execute (e.g., "ps", "logs container_name")
            
        Returns:
            Command output or error message
        """
        try:
            # Prepare the full command
            full_command = f"docker mcp gateway run {command}"
            
            logger.info(f"Executing Docker MCP command", command=command)
            
            # Execute the command
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Docker MCP command successful", command=command)
                return result.stdout
            else:
                logger.error(
                    f"Docker MCP command failed",
                    command=command,
                    error=result.stderr
                )
                return f"Error: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            logger.error(f"Docker MCP command timed out", command=command)
            return "Error: Command timed out after 30 seconds"
        except Exception as e:
            logger.error(f"Docker MCP command error", command=command, error=str(e))
            return f"Error: {str(e)}"


class DockerListContainersTool(DockerMCPTool):
    """List all Docker containers"""
    
    name: str = "docker_list_containers"
    description: str = "List all Docker containers with their status"
    
    def _run(self, filter: str = "") -> str:
        """List containers with optional filter"""
        command = "ps -a"
        if filter:
            command += f" --filter {filter}"
        return super()._run(command)


class DockerContainerLogsTool(DockerMCPTool):
    """Get Docker container logs"""
    
    name: str = "docker_container_logs"
    description: str = "Get logs from a Docker container"
    
    def _run(self, container_name: str, lines: int = 100) -> str:
        """Get container logs"""
        command = f"logs {container_name} --tail {lines}"
        return super()._run(command)


class DockerExecTool(DockerMCPTool):
    """Execute command in Docker container"""
    
    name: str = "docker_exec"
    description: str = "Execute a command inside a Docker container"
    
    def _run(self, container_name: str, exec_command: str) -> str:
        """Execute command in container"""
        command = f"exec {container_name} {exec_command}"
        return super()._run(command)


class DockerManageContainerTool(DockerMCPTool):
    """Start/stop/restart Docker containers"""
    
    name: str = "docker_manage_container"
    description: str = "Start, stop, or restart Docker containers"
    
    def _run(self, action: str, container_name: str) -> str:
        """Manage container state"""
        if action not in ["start", "stop", "restart"]:
            return f"Error: Invalid action '{action}'. Use 'start', 'stop', or 'restart'"
        
        command = f"{action} {container_name}"
        return super()._run(command)


def get_docker_tools() -> List[BaseTool]:
    """Get all Docker MCP tools"""
    return [
        DockerListContainersTool(),
        DockerContainerLogsTool(),
        DockerExecTool(),
        DockerManageContainerTool()
    ]