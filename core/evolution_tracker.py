"""
OKAMIシステム用進化トラッカー
システム進化・学習進捗・性能指標を記録
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import structlog

logger = structlog.get_logger()


class EvolutionTracker:
    """システム進化を記録・管理するクラス"""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        進化トラッカーの初期化

        Args:
            storage_dir: 進化データ保存ディレクトリ
        """
        self.storage_dir = storage_dir or os.path.join(os.getcwd(), "storage", "evolution")
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)

        self.evolution_file = os.path.join(self.storage_dir, "evolution_history.json")
        self.metrics_file = os.path.join(self.storage_dir, "performance_metrics.json")
        self.learning_file = os.path.join(self.storage_dir, "learning_insights.json")

        self._load_history()
        logger.info("Evolution Tracker initialized", storage_dir=self.storage_dir)

    def _load_history(self) -> None:
        """進化履歴を読み込む"""
        # Load evolution history
        if os.path.exists(self.evolution_file):
            with open(self.evolution_file, "r") as f:
                self.evolution_history = json.load(f)
        else:
            self.evolution_history = []

        # Load performance metrics
        if os.path.exists(self.metrics_file):
            with open(self.metrics_file, "r") as f:
                self.performance_metrics = json.load(f)
        else:
            self.performance_metrics = {}

        # Load learning insights
        if os.path.exists(self.learning_file):
            with open(self.learning_file, "r") as f:
                self.learning_insights = json.load(f)
        else:
            self.learning_insights = []

    def _save_history(self) -> None:
        """進化履歴を保存"""
        with open(self.evolution_file, "w") as f:
            json.dump(self.evolution_history, f, indent=2)

        with open(self.metrics_file, "w") as f:
            json.dump(self.performance_metrics, f, indent=2)

        with open(self.learning_file, "w") as f:
            json.dump(self.learning_insights, f, indent=2)

    def track_task_execution(
        self,
        task_id: str,
        agent_role: str,
        success: bool,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        タスク実行を記録

        Args:
            task_id: タスクID
            agent_role: 実行エージェント
            success: 成否
            execution_time: 実行時間
            metadata: 追加情報
        """
        execution_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "success": success,
            "execution_time": execution_time,
            "metadata": metadata or {},
        }

        self.evolution_history.append(execution_record)

        # Update agent metrics
        if agent_role not in self.performance_metrics:
            self.performance_metrics[agent_role] = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "total_execution_time": 0,
                "average_execution_time": 0,
            }

        metrics = self.performance_metrics[agent_role]
        metrics["total_tasks"] += 1
        if success:
            metrics["successful_tasks"] += 1
        else:
            metrics["failed_tasks"] += 1
        metrics["total_execution_time"] += execution_time
        metrics["average_execution_time"] = (
            metrics["total_execution_time"] / metrics["total_tasks"]
        )

        self._save_history()
        logger.info(
            "Task execution tracked",
            task_id=task_id,
            agent_role=agent_role,
            success=success,
        )

    def record_learning_insight(
        self,
        insight_type: str,
        description: str,
        source: str,
        impact_score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        学習インサイトを記録

        Args:
            insight_type: インサイト種別
            description: 説明
            source: ソース
            impact_score: 影響度
            metadata: 追加情報
        """
        insight = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": insight_type,
            "description": description,
            "source": source,
            "impact_score": impact_score,
            "metadata": metadata or {},
            "applied": False,
        }

        self.learning_insights.append(insight)
        self._save_history()
        logger.info(
            "Learning insight recorded", 
            insight_type=insight_type, 
            impact_score=impact_score
        )

    def get_agent_performance(self, agent_role: str) -> Dict[str, Any]:
        """
        エージェントの性能指標を取得

        Args:
            agent_role: エージェント役割

        Returns:
            性能指標
        """
        return self.performance_metrics.get(agent_role, {})

    def get_system_performance(self) -> Dict[str, Any]:
        """
        システム全体の性能指標を取得

        Returns:
            システム全体の指標
        """
        total_tasks = sum(m["total_tasks"] for m in self.performance_metrics.values())
        successful_tasks = sum(
            m["successful_tasks"] for m in self.performance_metrics.values()
        )
        
        if total_tasks == 0:
            return {
                "total_tasks": 0,
                "success_rate": 0,
                "total_agents": len(self.performance_metrics),
            }

        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": total_tasks - successful_tasks,
            "success_rate": successful_tasks / total_tasks,
            "total_agents": len(self.performance_metrics),
            "total_insights": len(self.learning_insights),
            "applied_insights": sum(
                1 for i in self.learning_insights if i.get("applied", False)
            ),
        }

    def get_recent_insights(
        self, limit: int = 10, min_impact: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        直近の高影響インサイトを取得

        Args:
            limit: 最大件数
            min_impact: 最小影響度

        Returns:
            インサイトリスト
        """
        filtered_insights = [
            i for i in self.learning_insights if i["impact_score"] >= min_impact
        ]
        
        # Sort by timestamp (most recent first)
        filtered_insights.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return filtered_insights[:limit]

    def mark_insight_applied(self, insight_index: int) -> None:
        """
        インサイトを適用済みにマーク

        Args:
            insight_index: インサイトのインデックス
        """
        if 0 <= insight_index < len(self.learning_insights):
            self.learning_insights[insight_index]["applied"] = True
            self.learning_insights[insight_index]["applied_at"] = (
                datetime.utcnow().isoformat()
            )
            self._save_history()
            logger.info("Insight marked as applied", insight_index=insight_index)

    def generate_evolution_report(self) -> Dict[str, Any]:
        """
        進化レポートを生成

        Returns:
            総合進化レポート
        """
        system_perf = self.get_system_performance()
        recent_insights = self.get_recent_insights()

        # Calculate evolution trends
        if len(self.evolution_history) >= 2:
            recent_executions = self.evolution_history[-100:]  # Last 100 executions
            recent_success_rate = sum(
                1 for e in recent_executions if e["success"]
            ) / len(recent_executions)
            
            older_executions = self.evolution_history[-200:-100] if len(
                self.evolution_history
            ) > 100 else self.evolution_history[:50]
            older_success_rate = sum(
                1 for e in older_executions if e["success"]
            ) / len(older_executions) if older_executions else 0
            
            improvement_rate = recent_success_rate - older_success_rate
        else:
            improvement_rate = 0

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "system_performance": system_perf,
            "agent_performances": self.performance_metrics,
            "recent_insights": recent_insights,
            "evolution_metrics": {
                "total_executions": len(self.evolution_history),
                "improvement_rate": improvement_rate,
                "learning_velocity": len(self.learning_insights) / max(
                    1, len(self.evolution_history)
                ),
            },
        }