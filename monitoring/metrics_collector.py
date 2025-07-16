"""
Metrics Collector for OKAMI monitoring
Collects and exposes system metrics
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
import json

logger = structlog.get_logger()


class MetricsCollector:
    """Collects and manages OKAMI system metrics"""

    def __init__(self):
        """Initialize metrics collector"""
        # Simple metrics storage
        self.metrics = {
            'task_executions': {'completed': 0, 'failed': 0},
            'task_durations': [],
            'agent_status': {},
            'agent_performance': {},
            'memory_operations': {'save': 0, 'load': 0, 'search': 0},
            'memory_size': 0,
            'knowledge_sources': {},
            'knowledge_queries': 0,
            'learning_insights': [],
            'evolution_score': 0.0,
            'system_info': {}
        }
        
        # Internal tracking
        self.metric_history: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("Metrics Collector initialized")

    def record_task_execution(
        self,
        crew: str,
        agent: str,
        status: str,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record task execution metrics

        Args:
            crew: Crew name
            agent: Agent role
            status: Execution status (success/failure)
            duration: Execution duration in seconds
            metadata: Additional metadata
        """
        # Update counters
        if status == 'success':
            self.metrics['task_executions']['completed'] += 1
        else:
            self.metrics['task_executions']['failed'] += 1
        
        # Record duration
        self.metrics['task_durations'].append(duration)
        # Keep only last 1000 durations
        if len(self.metrics['task_durations']) > 1000:
            self.metrics['task_durations'] = self.metrics['task_durations'][-1000:]
        
        # Store in history
        self._add_to_history('task_executions', {
            'timestamp': datetime.utcnow().isoformat(),
            'crew': crew,
            'agent': agent,
            'status': status,
            'duration': duration,
            'metadata': metadata or {}
        })
        
        logger.debug(
            "Task execution recorded",
            crew=crew,
            agent=agent,
            status=status,
            duration=duration
        )

    def update_agent_status(self, agent: str, active: bool) -> None:
        """
        Update agent status

        Args:
            agent: Agent role
            active: Whether agent is active
        """
        self.metrics['agent_status'][agent] = active

    def update_agent_performance(self, agent: str, success_rate: float) -> None:
        """
        Update agent performance metrics

        Args:
            agent: Agent role
            success_rate: Success rate (0-1)
        """
        self.metrics['agent_performance'][agent] = success_rate

    def record_memory_operation(
        self,
        operation: str,
        status: str,
        size_bytes: Optional[int] = None
    ) -> None:
        """
        Record memory operation

        Args:
            operation: Operation type (save/load/search)
            status: Operation status (success/failure)
            size_bytes: Size of memory data
        """
        if operation in self.metrics['memory_operations'] and status == 'success':
            self.metrics['memory_operations'][operation] += 1
        
        if size_bytes is not None:
            self.metrics['memory_size'] = size_bytes

    def update_knowledge_metrics(
        self,
        source_count: Dict[str, int],
        query_count: Optional[Dict[str, int]] = None
    ) -> None:
        """
        Update knowledge metrics

        Args:
            source_count: Count by source type
            query_count: Query count by source
        """
        self.metrics['knowledge_sources'] = source_count
        
        if query_count:
            self.metrics['knowledge_queries'] += sum(query_count.values())

    def record_learning_insight(
        self,
        insight_type: str,
        impact_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record learning insight

        Args:
            insight_type: Type of insight
            impact_score: Impact score (0-1)
            metadata: Additional metadata
        """
        # Determine impact level
        if impact_score >= 0.8:
            impact_level = 'high'
        elif impact_score >= 0.5:
            impact_level = 'medium'
        else:
            impact_level = 'low'
        
        insight_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': insight_type,
            'impact_score': impact_score,
            'impact_level': impact_level,
            'metadata': metadata or {}
        }
        
        self.metrics['learning_insights'].append(insight_data)
        # Keep only last 100 insights
        if len(self.metrics['learning_insights']) > 100:
            self.metrics['learning_insights'] = self.metrics['learning_insights'][-100:]
        
        # Store in history
        self._add_to_history('learning_insights', insight_data)

    def update_evolution_score(self, score: float) -> None:
        """
        Update system evolution score

        Args:
            score: Evolution score (0-1)
        """
        self.metrics['evolution_score'] = score

    def update_system_info(self, info: Dict[str, str]) -> None:
        """
        Update system information

        Args:
            info: System information dict
        """
        self.metrics['system_info'] = info

    def _add_to_history(self, metric_type: str, data: Dict[str, Any]) -> None:
        """Add data to metric history"""
        if metric_type not in self.metric_history:
            self.metric_history[metric_type] = []
        
        self.metric_history[metric_type].append(data)
        
        # Keep only last 1000 entries per metric type
        if len(self.metric_history[metric_type]) > 1000:
            self.metric_history[metric_type] = self.metric_history[metric_type][-1000:]

    def get_metrics_summary(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get metrics summary

        Args:
            time_window: Time window for metrics (default: last hour)

        Returns:
            Metrics summary
        """
        if time_window is None:
            time_window = timedelta(hours=1)
        
        cutoff_time = datetime.utcnow() - time_window
        
        summary = {
            'time_window': str(time_window),
            'generated_at': datetime.utcnow().isoformat(),
            'metrics': {}
        }
        
        # Task execution summary
        if 'task_executions' in self.metric_history:
            recent_tasks = [
                t for t in self.metric_history['task_executions']
                if datetime.fromisoformat(t['timestamp']) > cutoff_time
            ]
            
            if recent_tasks:
                total_tasks = len(recent_tasks)
                successful_tasks = len([t for t in recent_tasks if t['status'] == 'success'])
                avg_duration = sum(t['duration'] for t in recent_tasks) / total_tasks
                
                summary['metrics']['task_execution'] = {
                    'total': total_tasks,
                    'successful': successful_tasks,
                    'failed': total_tasks - successful_tasks,
                    'success_rate': successful_tasks / total_tasks,
                    'avg_duration': avg_duration
                }
        
        # Learning insights summary
        if 'learning_insights' in self.metric_history:
            recent_insights = [
                i for i in self.metric_history['learning_insights']
                if datetime.fromisoformat(i['timestamp']) > cutoff_time
            ]
            
            if recent_insights:
                summary['metrics']['learning'] = {
                    'total_insights': len(recent_insights),
                    'avg_impact_score': sum(i['impact_score'] for i in recent_insights) / len(recent_insights),
                    'high_impact_count': len([i for i in recent_insights if i['impact_level'] == 'high'])
                }
        
        # Add current metrics
        summary['metrics']['current'] = {
            'task_executions': self.metrics['task_executions'],
            'active_agents': sum(1 for v in self.metrics['agent_status'].values() if v),
            'evolution_score': self.metrics['evolution_score'],
            'knowledge_sources': len(self.metrics['knowledge_sources']),
            'knowledge_queries': self.metrics['knowledge_queries']
        }
        
        return summary

    def export_prometheus_metrics(self) -> bytes:
        """
        Export metrics in Prometheus format (simplified)

        Returns:
            Prometheus-style metrics as bytes
        """
        lines = []
        
        # Task metrics
        lines.append(f"# HELP okami_tasks_total Total number of tasks executed")
        lines.append(f"# TYPE okami_tasks_total counter")
        lines.append(f"okami_tasks_total{{status=\"completed\"}} {self.metrics['task_executions']['completed']}")
        lines.append(f"okami_tasks_total{{status=\"failed\"}} {self.metrics['task_executions']['failed']}")
        
        # Agent metrics
        lines.append(f"# HELP okami_agent_status Agent status (1=active, 0=inactive)")
        lines.append(f"# TYPE okami_agent_status gauge")
        for agent, active in self.metrics['agent_status'].items():
            lines.append(f"okami_agent_status{{agent=\"{agent}\"}} {1 if active else 0}")
        
        # Evolution score
        lines.append(f"# HELP okami_evolution_score System evolution score")
        lines.append(f"# TYPE okami_evolution_score gauge")
        lines.append(f"okami_evolution_score {self.metrics['evolution_score']}")
        
        return '\n'.join(lines).encode('utf-8')

    def export_json_metrics(self) -> str:
        """
        Export metrics in JSON format

        Returns:
            JSON string of metrics
        """
        metrics_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': self.get_metrics_summary(),
            'history': {
                k: v[-100:] for k, v in self.metric_history.items()  # Last 100 entries
            }
        }
        
        return json.dumps(metrics_data, indent=2)