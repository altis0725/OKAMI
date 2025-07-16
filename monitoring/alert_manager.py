"""
Alert Manager for OKAMI monitoring
Manages alerts and notifications
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import asyncio
import httpx
import structlog

logger = structlog.get_logger()


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Alert:
    """Alert data class"""
    
    def __init__(
        self,
        alert_id: str,
        title: str,
        description: str,
        severity: AlertSeverity,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.alert_id = alert_id
        self.title = title
        self.description = description
        self.severity = severity
        self.source = source
        self.status = AlertStatus.ACTIVE
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.acknowledged_at: Optional[datetime] = None
        self.resolved_at: Optional[datetime] = None
        self.metadata = metadata or {}
        self.notifications_sent = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "source": self.source,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
            "notifications_sent": self.notifications_sent,
        }


class AlertManager:
    """Manages alerts for OKAMI system"""

    def __init__(
        self,
        webhook_urls: Optional[List[str]] = None,
        alert_cooldown: int = 300  # 5 minutes
    ):
        """
        Initialize Alert Manager

        Args:
            webhook_urls: List of webhook URLs for notifications
            alert_cooldown: Cooldown period in seconds between similar alerts
        """
        self.webhook_urls = webhook_urls or []
        self.alert_cooldown = alert_cooldown
        
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.notification_handlers: Dict[str, Callable] = {}
        
        self._init_default_rules()
        logger.info(
            "Alert Manager initialized",
            webhook_count=len(self.webhook_urls),
            alert_cooldown=alert_cooldown
        )

    def _init_default_rules(self) -> None:
        """Initialize default alert rules"""
        # High failure rate rule
        self.add_rule({
            "name": "high_failure_rate",
            "condition": lambda metrics: metrics.get("success_rate", 1.0) < 0.5,
            "severity": AlertSeverity.HIGH,
            "title": "High Task Failure Rate",
            "description_template": "Task success rate is {success_rate:.1%}",
        })
        
        # System down rule
        self.add_rule({
            "name": "system_down",
            "condition": lambda metrics: metrics.get("system_status") == "down",
            "severity": AlertSeverity.CRITICAL,
            "title": "System Down",
            "description_template": "OKAMI system is not responding",
        })
        
        # All agents inactive
        self.add_rule({
            "name": "all_agents_inactive",
            "condition": lambda metrics: metrics.get("active_agents", 1) == 0,
            "severity": AlertSeverity.CRITICAL,
            "title": "All Agents Inactive",
            "description_template": "No active agents in the system",
        })
        
        # High memory usage
        self.add_rule({
            "name": "high_memory_usage",
            "condition": lambda metrics: metrics.get("memory_usage_percent", 0) > 90,
            "severity": AlertSeverity.MEDIUM,
            "title": "High Memory Usage",
            "description_template": "Memory usage at {memory_usage_percent}%",
        })

    def add_rule(self, rule: Dict[str, Any]) -> None:
        """
        Add alert rule

        Args:
            rule: Alert rule configuration
        """
        self.alert_rules.append(rule)
        logger.info(f"Alert rule added", rule_name=rule.get("name"))

    def check_rules(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        Check alert rules against metrics

        Args:
            metrics: System metrics

        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        for rule in self.alert_rules:
            try:
                # Check condition
                if rule["condition"](metrics):
                    alert_id = f"{rule['name']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                    
                    # Check if similar alert exists in cooldown period
                    if self._is_in_cooldown(rule["name"]):
                        continue
                    
                    # Format description
                    description = rule["description_template"].format(**metrics)
                    
                    # Create alert
                    alert = Alert(
                        alert_id=alert_id,
                        title=rule["title"],
                        description=description,
                        severity=rule["severity"],
                        source=rule["name"],
                        metadata={"metrics": metrics}
                    )
                    
                    triggered_alerts.append(alert)
                    
            except Exception as e:
                logger.error(f"Error checking rule", rule_name=rule.get("name"), error=str(e))
        
        return triggered_alerts

    def _is_in_cooldown(self, rule_name: str) -> bool:
        """Check if alert type is in cooldown"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.alert_cooldown)
        
        for alert in self.alerts.values():
            if (alert.source == rule_name and 
                alert.created_at > cutoff_time and
                alert.status == AlertStatus.ACTIVE):
                return True
        
        return False

    async def process_alerts(self, alerts: List[Alert]) -> None:
        """
        Process and send alerts

        Args:
            alerts: List of alerts to process
        """
        for alert in alerts:
            # Store alert
            self.alerts[alert.alert_id] = alert
            
            # Send notifications
            await self._send_notifications(alert)
            
            logger.info(
                "Alert processed",
                alert_id=alert.alert_id,
                severity=alert.severity.value,
                title=alert.title
            )

    async def _send_notifications(self, alert: Alert) -> None:
        """Send notifications for alert"""
        notification_tasks = []
        
        # Send to webhooks
        for webhook_url in self.webhook_urls:
            notification_tasks.append(
                self._send_webhook_notification(webhook_url, alert)
            )
        
        # Send to custom handlers
        for handler_name, handler in self.notification_handlers.items():
            notification_tasks.append(
                self._send_custom_notification(handler_name, handler, alert)
            )
        
        # Execute all notifications concurrently
        results = await asyncio.gather(*notification_tasks, return_exceptions=True)
        
        # Count successful notifications
        successful_notifications = sum(1 for r in results if r is True)
        alert.notifications_sent = successful_notifications

    async def _send_webhook_notification(self, webhook_url: str, alert: Alert) -> bool:
        """Send webhook notification"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json={
                        "alert": alert.to_dict(),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.debug(f"Webhook notification sent", webhook_url=webhook_url)
                    return True
                else:
                    logger.warning(
                        f"Webhook notification failed",
                        webhook_url=webhook_url,
                        status_code=response.status_code
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Webhook notification error", webhook_url=webhook_url, error=str(e))
            return False

    async def _send_custom_notification(
        self, handler_name: str, handler: Callable, alert: Alert
    ) -> bool:
        """Send custom notification"""
        try:
            await handler(alert)
            logger.debug(f"Custom notification sent", handler=handler_name)
            return True
        except Exception as e:
            logger.error(f"Custom notification error", handler=handler_name, error=str(e))
            return False

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert

        Args:
            alert_id: Alert ID

        Returns:
            Success status
        """
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            
            logger.info("Alert acknowledged", alert_id=alert_id)
            return True
        
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert

        Args:
            alert_id: Alert ID

        Returns:
            Success status
        """
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            
            logger.info("Alert resolved", alert_id=alert_id)
            return True
        
        return False

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [
            alert for alert in self.alerts.values()
            if alert.status == AlertStatus.ACTIVE
        ]

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary"""
        active_alerts = self.get_active_alerts()
        
        # Count by severity
        severity_counts = {
            AlertSeverity.LOW.value: 0,
            AlertSeverity.MEDIUM.value: 0,
            AlertSeverity.HIGH.value: 0,
            AlertSeverity.CRITICAL.value: 0,
        }
        
        for alert in active_alerts:
            severity_counts[alert.severity.value] += 1
        
        return {
            "total_alerts": len(self.alerts),
            "active_alerts": len(active_alerts),
            "acknowledged_alerts": len([a for a in self.alerts.values() if a.status == AlertStatus.ACKNOWLEDGED]),
            "resolved_alerts": len([a for a in self.alerts.values() if a.status == AlertStatus.RESOLVED]),
            "severity_counts": severity_counts,
            "recent_alerts": [a.to_dict() for a in sorted(active_alerts, key=lambda x: x.created_at, reverse=True)[:10]],
        }

    def add_notification_handler(self, name: str, handler: Callable) -> None:
        """
        Add custom notification handler

        Args:
            name: Handler name
            handler: Async callable that takes Alert as parameter
        """
        self.notification_handlers[name] = handler
        logger.info(f"Notification handler added", handler_name=name)