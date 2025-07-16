"""
OKAMI Logger Configuration
Structured logging with multiple outputs and debug capabilities
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import structlog
from structlog.processors import CallsiteParameter


class OkamiLogger:
    """Custom logger for OKAMI system"""

    def __init__(
        self,
        log_dir: str = "logs",
        log_level: str = "INFO",
        enable_json: bool = True,
        enable_console: bool = True,
        enable_file: bool = True,
    ):
        """
        Initialize OKAMI Logger

        Args:
            log_dir: Directory for log files
            log_level: Logging level
            enable_json: Enable JSON formatting
            enable_console: Enable console output
            enable_file: Enable file output
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.enable_json = enable_json
        self.enable_console = enable_console
        self.enable_file = enable_file
        
        self._configure_structlog()
        self._configure_standard_logging()

    def _configure_structlog(self) -> None:
        """Configure structlog"""
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    CallsiteParameter.FILENAME,
                    CallsiteParameter.FUNC_NAME,
                    CallsiteParameter.LINENO,
                ]
            ),
        ]

        # Add custom OKAMI context
        processors.append(self._add_okami_context)

        if self.enable_json:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(
                structlog.dev.ConsoleRenderer(
                    colors=sys.stdout.isatty(),
                    exception_formatter=structlog.dev.rich_traceback,
                )
            )

        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    def _configure_standard_logging(self) -> None:
        """Configure standard logging"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(self._get_formatter())
            root_logger.addHandler(console_handler)

        # File handler
        if self.enable_file:
            log_file = self.log_dir / f"okami_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(self._get_formatter())
            root_logger.addHandler(file_handler)

            # Error file handler
            error_file = self.log_dir / f"okami_errors_{datetime.now().strftime('%Y%m%d')}.log"
            error_handler = logging.FileHandler(error_file, encoding='utf-8')
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(self._get_formatter())
            root_logger.addHandler(error_handler)

    def _get_formatter(self) -> logging.Formatter:
        """Get log formatter"""
        if self.enable_json:
            return logging.Formatter('%(message)s')
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

    def _add_okami_context(
        self, logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add OKAMI-specific context to logs"""
        # Add system context
        event_dict["okami_version"] = "0.1.0"
        
        # Add environment context
        if os.getenv("OKAMI_CREW_NAME"):
            event_dict["crew"] = os.getenv("OKAMI_CREW_NAME")
        
        if os.getenv("OKAMI_AGENT_ROLE"):
            event_dict["agent"] = os.getenv("OKAMI_AGENT_ROLE")
        
        # Add execution context if available
        if hasattr(logger, '_okami_context'):
            event_dict.update(logger._okami_context)
        
        return event_dict

    def get_logger(self, name: str) -> structlog.BoundLogger:
        """
        Get a logger instance

        Args:
            name: Logger name

        Returns:
            Configured logger
        """
        return structlog.get_logger(name)

    def add_context(self, logger: structlog.BoundLogger, **kwargs) -> structlog.BoundLogger:
        """
        Add context to logger

        Args:
            logger: Logger instance
            **kwargs: Context key-value pairs

        Returns:
            Logger with context
        """
        return logger.bind(**kwargs)

    def create_debug_logger(self, name: str, debug_file: Optional[str] = None) -> structlog.BoundLogger:
        """
        Create a debug logger with detailed output

        Args:
            name: Logger name
            debug_file: Optional debug file path

        Returns:
            Debug logger
        """
        debug_logger = self.get_logger(name)
        
        if debug_file:
            debug_path = self.log_dir / debug_file
            debug_handler = logging.FileHandler(debug_path, encoding='utf-8')
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(self._get_formatter())
            
            logger = logging.getLogger(name)
            logger.addHandler(debug_handler)
            logger.setLevel(logging.DEBUG)
        
        return debug_logger

    def log_performance(
        self,
        logger: structlog.BoundLogger,
        operation: str,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log performance metrics

        Args:
            logger: Logger instance
            operation: Operation name
            duration: Duration in seconds
            metadata: Additional metadata
        """
        log_data = {
            "operation": operation,
            "duration_ms": duration * 1000,
            "performance": True,
        }
        
        if metadata:
            log_data.update(metadata)
        
        logger.info("Performance metric", **log_data)

    def log_agent_action(
        self,
        logger: structlog.BoundLogger,
        action: str,
        agent_role: str,
        task: Optional[str] = None,
        result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log agent action

        Args:
            logger: Logger instance
            action: Action type
            agent_role: Agent role
            task: Task description
            result: Action result
            metadata: Additional metadata
        """
        log_data = {
            "agent_action": action,
            "agent_role": agent_role,
            "agent_event": True,
        }
        
        if task:
            log_data["task"] = task[:200]  # Truncate long tasks
        
        if result:
            log_data["result"] = result[:200]  # Truncate long results
        
        if metadata:
            log_data.update(metadata)
        
        logger.info("Agent action", **log_data)

    def log_crew_event(
        self,
        logger: structlog.BoundLogger,
        event: str,
        crew_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log crew event

        Args:
            logger: Logger instance
            event: Event type
            crew_name: Crew name
            metadata: Additional metadata
        """
        log_data = {
            "crew_event": event,
            "crew_name": crew_name,
            "crew_log": True,
        }
        
        if metadata:
            log_data.update(metadata)
        
        logger.info("Crew event", **log_data)


# Global logger instance
_logger_instance: Optional[OkamiLogger] = None


def initialize_logger(
    log_dir: str = "logs",
    log_level: str = None,
    enable_json: bool = None,
    enable_console: bool = True,
    enable_file: bool = True,
) -> OkamiLogger:
    """
    Initialize global logger

    Args:
        log_dir: Directory for log files
        log_level: Logging level
        enable_json: Enable JSON formatting
        enable_console: Enable console output
        enable_file: Enable file output

    Returns:
        Logger instance
    """
    global _logger_instance
    
    # Get from environment if not provided
    if log_level is None:
        log_level = os.getenv("OKAMI_LOG_LEVEL", "INFO")
    
    if enable_json is None:
        enable_json = os.getenv("OKAMI_LOG_JSON", "true").lower() == "true"
    
    _logger_instance = OkamiLogger(
        log_dir=log_dir,
        log_level=log_level,
        enable_json=enable_json,
        enable_console=enable_console,
        enable_file=enable_file,
    )
    
    return _logger_instance


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """
    Get a logger instance

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = initialize_logger()
    
    return _logger_instance.get_logger(name)