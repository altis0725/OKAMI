"""
OKAMIシステム用進化トラッカー
システム進化・学習進捗・性能指標を記録
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import structlog
from collections import defaultdict, Counter
import re

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
        self.patterns_file = os.path.join(self.storage_dir, "task_patterns.json")

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
            
        # Load task patterns
        if os.path.exists(self.patterns_file):
            with open(self.patterns_file, "r") as f:
                self.task_patterns = json.load(f)
        else:
            self.task_patterns = {
                "success_patterns": defaultdict(list),
                "failure_patterns": defaultdict(list),
                "common_outputs": defaultdict(list),
                "task_keywords": defaultdict(int)
            }

    def _save_history(self) -> None:
        """進化履歴を保存"""
        with open(self.evolution_file, "w") as f:
            json.dump(self.evolution_history, f, indent=2)

        with open(self.metrics_file, "w") as f:
            json.dump(self.performance_metrics, f, indent=2)

        with open(self.learning_file, "w") as f:
            json.dump(self.learning_insights, f, indent=2)
            
        # Convert defaultdict to regular dict for JSON serialization
        patterns_to_save = {
            "success_patterns": dict(self.task_patterns.get("success_patterns", {})),
            "failure_patterns": dict(self.task_patterns.get("failure_patterns", {})),
            "common_outputs": dict(self.task_patterns.get("common_outputs", {})),
            "task_keywords": dict(self.task_patterns.get("task_keywords", {}))
        }
        with open(self.patterns_file, "w") as f:
            json.dump(patterns_to_save, f, indent=2)

    def track_task_execution(
        self,
        agent_role: str,
        task_description: Optional[str] = None,
        execution_time: float = 0.0,
        success: bool = True,
        output: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """
        タスク実行を記録

        Args:
            agent_role: 実行エージェント
            task_description: タスク説明
            execution_time: 実行時間
            success: 成否
            output: タスク出力
            metadata: 追加情報
            task_id: タスクID
        """
        execution_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "agent_role": agent_role,
            "task_description": task_description,
            "success": success,
            "execution_time": execution_time,
            "output": output,
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

        # Analyze task patterns
        if task_description and output:
            self._analyze_task_patterns(
                agent_role=agent_role,
                task_description=task_description,
                output=output,
                success=success,
                execution_time=execution_time
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
    
    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        # 簡単なキーワード抽出（英数字の単語を抽出）
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        # ストップワードの簡易フィルタリング
        stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'are', 'was', 'were', 'been', 'have', 'has', 'had'}
        return [w for w in words if w not in stop_words]
    
    def _analyze_task_patterns(
        self,
        agent_role: str,
        task_description: str,
        output: Any,
        success: bool,
        execution_time: float
    ) -> None:
        """タスクの実行パターンを分析"""
        # キーワード抽出
        keywords = self._extract_keywords(task_description)
        output_str = str(output) if output else ""
        
        # タスクキーワードの頻度を記録
        if not isinstance(self.task_patterns.get("task_keywords"), dict):
            self.task_patterns["task_keywords"] = {}
        
        for keyword in keywords:
            if keyword not in self.task_patterns["task_keywords"]:
                self.task_patterns["task_keywords"][keyword] = 0
            self.task_patterns["task_keywords"][keyword] += 1
        
        # 成功/失敗パターンの記録
        pattern_key = "success_patterns" if success else "failure_patterns"
        if not isinstance(self.task_patterns.get(pattern_key), dict):
            self.task_patterns[pattern_key] = {}
            
        if agent_role not in self.task_patterns[pattern_key]:
            self.task_patterns[pattern_key][agent_role] = []
            
        self.task_patterns[pattern_key][agent_role].append({
            "task_description": task_description,
            "keywords": keywords,
            "execution_time": execution_time,
            "output_length": len(output_str),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # 共通の出力パターンを記録
        if output_str and success:
            if not isinstance(self.task_patterns.get("common_outputs"), dict):
                self.task_patterns["common_outputs"] = {}
                
            if agent_role not in self.task_patterns["common_outputs"]:
                self.task_patterns["common_outputs"][agent_role] = []
                
            # 出力の最初の200文字を保存（パターン認識のため）
            self.task_patterns["common_outputs"][agent_role].append({
                "output_preview": output_str[:200],
                "task_keywords": keywords,
                "full_length": len(output_str)
            })
        
        # パターンから学習インサイトを生成
        self._generate_pattern_insights(agent_role)
    
    def _generate_pattern_insights(self, agent_role: str) -> None:
        """パターンから学習インサイトを生成"""
        # エージェントの成功率を計算
        metrics = self.performance_metrics.get(agent_role, {})
        if metrics.get("total_tasks", 0) < 5:
            return  # 十分なデータがない
            
        success_rate = metrics["successful_tasks"] / metrics["total_tasks"]
        
        # 低い成功率の場合、失敗パターンを分析
        if success_rate < 0.7:
            failure_patterns = self.task_patterns.get("failure_patterns", {}).get(agent_role, [])
            if len(failure_patterns) >= 3:
                # 共通する失敗キーワードを見つける
                all_keywords = []
                for pattern in failure_patterns[-5:]:  # 最新5件
                    all_keywords.extend(pattern.get("keywords", []))
                
                keyword_counter = Counter(all_keywords)
                common_keywords = [k for k, v in keyword_counter.items() if v >= 2]
                
                if common_keywords:
                    self.record_learning_insight(
                        insight_type="failure_pattern",
                        description=f"Agent {agent_role} frequently fails on tasks containing: {', '.join(common_keywords)}",
                        source=f"pattern_analysis_{agent_role}",
                        impact_score=0.8,
                        metadata={
                            "agent_role": agent_role,
                            "success_rate": success_rate,
                            "common_keywords": common_keywords
                        }
                    )
        
        # 実行時間のパターンを分析
        avg_time = metrics.get("average_execution_time", 0)
        if avg_time > 30:  # 30秒以上かかる場合
            self.record_learning_insight(
                insight_type="performance_issue",
                description=f"Agent {agent_role} has high average execution time: {avg_time:.2f}s",
                source=f"performance_analysis_{agent_role}",
                impact_score=0.6,
                metadata={
                    "agent_role": agent_role,
                    "average_time": avg_time
                }
            )
    
    def get_improvement_suggestions(self) -> List[Dict[str, Any]]:
        """改善提案を生成"""
        suggestions = []
        
        # 各エージェントのパフォーマンスを分析
        for agent_role, metrics in self.performance_metrics.items():
            if metrics["total_tasks"] < 5:
                continue
                
            success_rate = metrics["successful_tasks"] / metrics["total_tasks"]
            
            # 成功率が低いエージェントへの提案
            if success_rate < 0.7:
                failure_patterns = self.task_patterns.get("failure_patterns", {}).get(agent_role, [])
                if failure_patterns:
                    recent_failures = failure_patterns[-3:]
                    suggestions.append({
                        "agent_role": agent_role,
                        "type": "skill_improvement",
                        "priority": "high",
                        "suggestion": f"Agent {agent_role} needs improvement. Success rate: {success_rate:.1%}",
                        "details": {
                            "recent_failure_tasks": [p["task_description"] for p in recent_failures],
                            "recommended_actions": [
                                "Review and enhance agent's goal and backstory",
                                "Add more specific tools or knowledge sources",
                                "Consider breaking complex tasks into smaller subtasks"
                            ]
                        }
                    })
            
            # 実行時間が長いエージェントへの提案
            avg_time = metrics.get("average_execution_time", 0)
            if avg_time > 30:
                suggestions.append({
                    "agent_role": agent_role,
                    "type": "performance_optimization",
                    "priority": "medium",
                    "suggestion": f"Agent {agent_role} has slow execution time: {avg_time:.1f}s average",
                    "details": {
                        "current_avg_time": avg_time,
                        "recommended_actions": [
                            "Optimize task descriptions to be more specific",
                            "Review and optimize tool usage",
                            "Consider caching frequently accessed data"
                        ]
                    }
                })
        
        # 全体的なシステム改善提案
        system_perf = self.get_system_performance()
        if system_perf["total_tasks"] > 20:
            overall_success_rate = system_perf["successful_tasks"] / system_perf["total_tasks"]
            if overall_success_rate < 0.8:
                suggestions.append({
                    "agent_role": "system",
                    "type": "system_improvement",
                    "priority": "high",
                    "suggestion": f"Overall system success rate needs improvement: {overall_success_rate:.1%}",
                    "details": {
                        "total_tasks": system_perf["total_tasks"],
                        "failed_tasks": system_perf["failed_tasks"],
                        "recommended_actions": [
                            "Implement better error handling and retry mechanisms",
                            "Add validation steps between agent handoffs",
                            "Consider adding a supervisor agent for complex workflows"
                        ]
                    }
                })
        
        return suggestions