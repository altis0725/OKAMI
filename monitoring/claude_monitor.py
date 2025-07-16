"""
Claude Code Monitor for OKAMI system
External monitoring and intervention system
"""

import os
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import httpx
import structlog

logger = structlog.get_logger()

# Simple metrics storage (instead of Prometheus)
metrics = {
    'task_executions': {'completed': 0, 'failed': 0},
    'task_durations': [],
    'system_health': 1.0
}


class ClaudeMonitor:
    """External monitor for OKAMI system using Claude Code"""

    def __init__(
        self,
        okami_api_url: str = "http://localhost:8000",
        monitor_interval: int = 60,
        webhook_url: Optional[str] = None,
    ):
        """
        Initialize Claude Monitor

        Args:
            okami_api_url: OKAMI API URL
            monitor_interval: Monitoring interval in seconds
            webhook_url: Optional webhook for alerts
        """
        self.okami_api_url = okami_api_url
        self.monitor_interval = monitor_interval
        self.webhook_url = webhook_url or os.getenv("CLAUDE_MONITOR_WEBHOOK_URL")
        
        self.client = httpx.AsyncClient(timeout=30.0)
        self.monitoring_active = False
        self.last_health_check = None
        self.alert_history: List[Dict[str, Any]] = []
        
        logger.info(
            "Claude Monitor initialized",
            okami_api_url=okami_api_url,
            monitor_interval=monitor_interval,
            has_webhook=bool(self.webhook_url),
        )

    async def start_monitoring(self) -> None:
        """Start the monitoring loop"""
        self.monitoring_active = True
        logger.info("Claude Monitor started")
        
        while self.monitoring_active:
            try:
                await self._monitor_cycle()
                await asyncio.sleep(self.monitor_interval)
            except Exception as e:
                logger.error(f"Monitor cycle error: {e}")
                await asyncio.sleep(5)  # Short delay on error

    async def stop_monitoring(self) -> None:
        """Stop the monitoring loop"""
        self.monitoring_active = False
        await self.client.aclose()
        logger.info("Claude Monitor stopped")

    async def _monitor_cycle(self) -> None:
        """Single monitoring cycle"""
        # Collect system metrics
        metrics = await self._collect_metrics()
        
        # Analyze system health
        health_score = self._analyze_health(metrics)
        metrics['system_health'] = health_score
        
        # Check for anomalies
        anomalies = self._detect_anomalies(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, anomalies)
        
        # Send alerts if needed
        if anomalies or health_score < 0.7:
            await self._send_alert({
                "timestamp": datetime.utcnow().isoformat(),
                "health_score": health_score,
                "anomalies": anomalies,
                "recommendations": recommendations,
                "metrics": metrics,
            })
        
        # Log monitoring results
        logger.info(
            "Monitor cycle completed",
            health_score=health_score,
            anomalies_count=len(anomalies),
            recommendations_count=len(recommendations),
        )

    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics from OKAMI system"""
        metrics = {}
        
        try:
            # Get system status
            response = await self.client.get(f"{self.okami_api_url}/status")
            if response.status_code == 200:
                metrics["system_status"] = response.json()
            
            # Get performance metrics
            response = await self.client.get(f"{self.okami_api_url}/metrics")
            if response.status_code == 200:
                metrics["performance"] = response.json()
            
            # Get agent statuses
            response = await self.client.get(f"{self.okami_api_url}/agents")
            if response.status_code == 200:
                agents_data = response.json()
                metrics["agents"] = agents_data
                metrics['active_agents'] = len([a for a in agents_data if a.get("active", False)])
            
            # Get knowledge info
            response = await self.client.get(f"{self.okami_api_url}/knowledge")
            if response.status_code == 200:
                knowledge_data = response.json()
                metrics["knowledge"] = knowledge_data
                metrics["knowledge_collections"] = len(knowledge_data.get("collections", []))
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            metrics["error"] = str(e)
        
        return metrics

    def _analyze_health(self, metrics: Dict[str, Any]) -> float:
        """
        Analyze system health

        Args:
            metrics: System metrics

        Returns:
            Health score (0-1)
        """
        if "error" in metrics:
            return 0.0
        
        health_factors = []
        
        # Check system status
        if "system_status" in metrics:
            status = metrics["system_status"]
            if status.get("status") == "healthy":
                health_factors.append(1.0)
            else:
                health_factors.append(0.5)
        
        # Check performance metrics
        if "performance" in metrics:
            perf = metrics["performance"]
            success_rate = perf.get("success_rate", 0)
            health_factors.append(success_rate)
            
            # Check response time
            avg_response_time = perf.get("avg_response_time", float('inf'))
            if avg_response_time < 1.0:
                health_factors.append(1.0)
            elif avg_response_time < 5.0:
                health_factors.append(0.7)
            else:
                health_factors.append(0.3)
        
        # Check agent health
        if "agents" in metrics:
            agents = metrics["agents"]
            if agents:
                active_ratio = len([a for a in agents if a.get("active", False)]) / len(agents)
                health_factors.append(active_ratio)
        
        # Calculate overall health
        if health_factors:
            return sum(health_factors) / len(health_factors)
        return 0.5

    def _detect_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect anomalies in system behavior

        Args:
            metrics: System metrics

        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Check for system errors
        if "error" in metrics:
            anomalies.append({
                "type": "system_error",
                "severity": "high",
                "description": f"System error: {metrics['error']}",
            })
        
        # Check performance anomalies
        if "performance" in metrics:
            perf = metrics["performance"]
            
            # Low success rate
            if perf.get("success_rate", 1.0) < 0.5:
                anomalies.append({
                    "type": "low_success_rate",
                    "severity": "high",
                    "description": f"Success rate below 50%: {perf['success_rate']:.2%}",
                })
            
            # High response time
            if perf.get("avg_response_time", 0) > 10.0:
                anomalies.append({
                    "type": "high_response_time",
                    "severity": "medium",
                    "description": f"High average response time: {perf['avg_response_time']:.2f}s",
                })
        
        # Check agent anomalies
        if "agents" in metrics:
            agents = metrics["agents"]
            
            # All agents inactive
            if agents and not any(a.get("active", False) for a in agents):
                anomalies.append({
                    "type": "all_agents_inactive",
                    "severity": "critical",
                    "description": "All agents are inactive",
                })
            
            # Agent failure patterns
            for agent in agents:
                if agent.get("failure_rate", 0) > 0.3:
                    anomalies.append({
                        "type": "agent_high_failure_rate",
                        "severity": "medium",
                        "description": f"Agent '{agent['role']}' has high failure rate: {agent['failure_rate']:.2%}",
                        "agent": agent["role"],
                    })
        
        return anomalies

    def _generate_recommendations(
        self, metrics: Dict[str, Any], anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on metrics and anomalies

        Args:
            metrics: System metrics
            anomalies: Detected anomalies

        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Recommendations based on anomalies
        for anomaly in anomalies:
            if anomaly["type"] == "low_success_rate":
                recommendations.append({
                    "type": "review_guardrails",
                    "priority": "high",
                    "description": "Review and adjust task guardrails to improve success rate",
                    "action": "Consider relaxing overly strict validation rules",
                })
            
            elif anomaly["type"] == "high_response_time":
                recommendations.append({
                    "type": "optimize_performance",
                    "priority": "medium",
                    "description": "Optimize task execution for better performance",
                    "action": "Enable caching, reduce task complexity, or add more resources",
                })
            
            elif anomaly["type"] == "all_agents_inactive":
                recommendations.append({
                    "type": "restart_agents",
                    "priority": "critical",
                    "description": "Restart the agent system",
                    "action": "Check logs for errors and restart the OKAMI service",
                })
            
            elif anomaly["type"] == "agent_high_failure_rate":
                recommendations.append({
                    "type": "agent_optimization",
                    "priority": "medium",
                    "description": f"Optimize agent '{anomaly.get('agent', 'unknown')}'",
                    "action": "Review agent configuration, tools, and knowledge sources",
                })
        
        # General recommendations based on metrics
        if "performance" in metrics:
            perf = metrics["performance"]
            
            # Learning recommendations
            if perf.get("learning_insights_count", 0) > 10:
                recommendations.append({
                    "type": "apply_insights",
                    "priority": "low",
                    "description": "Apply accumulated learning insights",
                    "action": "Review and implement high-impact learning insights",
                })
        
        return recommendations

    async def _send_alert(self, alert_data: Dict[str, Any]) -> None:
        """
        Send alert via webhook

        Args:
            alert_data: Alert information
        """
        self.alert_history.append(alert_data)
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
        
        if self.webhook_url:
            try:
                response = await self.client.post(
                    self.webhook_url,
                    json=alert_data,
                    headers={"Content-Type": "application/json"},
                )
                logger.info(
                    "Alert sent",
                    status_code=response.status_code,
                    health_score=alert_data["health_score"],
                )
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

    async def get_monitoring_report(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring report

        Returns:
            Monitoring report
        """
        current_metrics = await self._collect_metrics()
        health_score = self._analyze_health(current_metrics)
        anomalies = self._detect_anomalies(current_metrics)
        recommendations = self._generate_recommendations(current_metrics, anomalies)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health_score": health_score,
            "metrics": current_metrics,
            "anomalies": anomalies,
            "recommendations": recommendations,
            "alert_history": self.alert_history[-10:],  # Last 10 alerts
            "monitoring_status": {
                "active": self.monitoring_active,
                "interval": self.monitor_interval,
                "last_check": self.last_health_check,
            },
        }


async def main():
    """Main function for running the monitor"""
    monitor = ClaudeMonitor(
        okami_api_url=os.getenv("OKAMI_API_URL", "http://localhost:8000"),
        monitor_interval=int(os.getenv("MONITOR_INTERVAL", "60")),
    )
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
        await monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())