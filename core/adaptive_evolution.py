"""
自己適応型進化エンジン

パフォーマンスメトリクスに基づいて自動的にシステムを調整し、
知識グラフと連携して継続的な改善を実現。
"""

import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import structlog

from .evolution_tracker import EvolutionTracker
from .knowledge_graph import KnowledgeGraphManager, KnowledgeNode, KnowledgeRelation
from evolution.improvement_parser import ImprovementParser
from evolution.improvement_applier import ImprovementApplier

logger = structlog.get_logger()


class AdaptiveEvolutionEngine:
    """
    自己適応型進化エンジン
    
    システムパフォーマンスを監視し、自動的に改善を適用
    """
    
    def __init__(self, 
                 evolution_tracker: Optional[EvolutionTracker] = None,
                 knowledge_graph: Optional[KnowledgeGraphManager] = None,
                 auto_apply_threshold: float = 0.8,
                 min_data_points: int = 100):
        """
        初期化
        
        Args:
            evolution_tracker: 進化トラッカー
            knowledge_graph: 知識グラフマネージャー
            auto_apply_threshold: 自動適用の信頼度閾値
            min_data_points: 適応に必要な最小データポイント数
        """
        self.tracker = evolution_tracker or EvolutionTracker()
        self.knowledge_graph = knowledge_graph or KnowledgeGraphManager()
        self.parser = ImprovementParser()
        self.applier = ImprovementApplier()
        
        self.auto_apply_threshold = auto_apply_threshold
        self.min_data_points = min_data_points
        
        # 適応パラメータ
        self.adaptation_params = {
            "learning_rate": 0.1,
            "exploration_rate": 0.2,
            "momentum": 0.9,
            "decay_rate": 0.95
        }
        
        # パフォーマンス履歴
        self.performance_history = []
        self.load_performance_history()
        
        logger.info("Adaptive Evolution Engine initialized",
                   auto_apply_threshold=auto_apply_threshold,
                   min_data_points=min_data_points)
    
    def analyze_performance_trends(self) -> Dict[str, Any]:
        """
        パフォーマンストレンドを分析
        
        Returns:
            トレンド分析結果
        """
        system_perf = self.tracker.get_system_performance()
        
        if system_perf["total_tasks"] < self.min_data_points:
            return {
                "status": "insufficient_data",
                "message": f"需要至少{self.min_data_points}个数据点进行分析"
            }
        
        # エージェント別のパフォーマンス分析
        agent_trends = {}
        for agent_role, metrics in self.tracker.performance_metrics.items():
            if metrics["total_tasks"] >= 10:  # 最小タスク数
                agent_trends[agent_role] = self._calculate_agent_trend(agent_role, metrics)
        
        # システム全体のトレンド
        system_trend = self._calculate_system_trend()
        
        # 改善が必要な領域を特定
        improvement_areas = self._identify_improvement_areas(agent_trends, system_trend)
        
        return {
            "status": "analyzed",
            "system_trend": system_trend,
            "agent_trends": agent_trends,
            "improvement_areas": improvement_areas,
            "recommendations": self._generate_recommendations(improvement_areas)
        }
    
    def _calculate_agent_trend(self, agent_role: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """エージェントのトレンドを計算"""
        # 最近の実行履歴を取得
        recent_executions = [
            e for e in self.tracker.evolution_history[-100:]
            if e.get("agent_role") == agent_role
        ]
        
        if len(recent_executions) < 5:
            return {"trend": "stable", "confidence": 0.0}
        
        # 成功率の移動平均を計算
        window_size = min(10, len(recent_executions) // 2)
        success_rates = []
        
        for i in range(len(recent_executions) - window_size + 1):
            window = recent_executions[i:i + window_size]
            success_rate = sum(1 for e in window if e["success"]) / window_size
            success_rates.append(success_rate)
        
        if len(success_rates) < 2:
            return {"trend": "stable", "confidence": 0.0}
        
        # トレンドを計算（線形回帰）
        x = np.arange(len(success_rates))
        y = np.array(success_rates)
        
        # 線形回帰
        slope = np.polyfit(x, y, 1)[0]
        
        # トレンドの判定
        if slope > 0.01:
            trend = "improving"
        elif slope < -0.01:
            trend = "declining"
        else:
            trend = "stable"
        
        # 信頼度（R²値の簡易版）
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        ss_res = np.sum((y - (slope * x + y[0])) ** 2)
        confidence = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            "trend": trend,
            "slope": float(slope),
            "confidence": float(confidence),
            "current_success_rate": float(y[-1]) if y.size > 0 else 0,
            "average_execution_time": metrics["average_execution_time"]
        }
    
    def _calculate_system_trend(self) -> Dict[str, Any]:
        """システム全体のトレンドを計算"""
        if len(self.performance_history) < 2:
            return {"trend": "stable", "confidence": 0.0}
        
        # 最近のパフォーマンス指標
        recent_perfs = self.performance_history[-20:]
        
        if len(recent_perfs) < 5:
            return {"trend": "stable", "confidence": 0.0}
        
        # 複合スコアを計算
        scores = []
        for perf in recent_perfs:
            score = (
                perf.get("success_rate", 0) * 0.4 +
                (1 - perf.get("avg_execution_time", 1) / 10) * 0.3 +
                perf.get("learning_velocity", 0) * 0.3
            )
            scores.append(score)
        
        # トレンド分析
        x = np.arange(len(scores))
        y = np.array(scores)
        slope = np.polyfit(x, y, 1)[0]
        
        if slope > 0.005:
            trend = "improving"
        elif slope < -0.005:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "slope": float(slope),
            "current_score": float(y[-1]) if y.size > 0 else 0,
            "average_score": float(np.mean(y))
        }
    
    def _identify_improvement_areas(self, 
                                  agent_trends: Dict[str, Dict[str, Any]], 
                                  system_trend: Dict[str, Any]) -> List[Dict[str, Any]]:
        """改善が必要な領域を特定"""
        improvement_areas = []
        
        # パフォーマンスが低下しているエージェントを特定
        for agent_role, trend_data in agent_trends.items():
            if trend_data["trend"] == "declining" and trend_data["confidence"] > 0.6:
                improvement_areas.append({
                    "type": "agent_performance",
                    "agent": agent_role,
                    "issue": "performance_decline",
                    "severity": "high" if trend_data["slope"] < -0.02 else "medium",
                    "metrics": trend_data
                })
            elif trend_data["current_success_rate"] < 0.7:
                improvement_areas.append({
                    "type": "agent_performance",
                    "agent": agent_role,
                    "issue": "low_success_rate",
                    "severity": "high" if trend_data["current_success_rate"] < 0.5 else "medium",
                    "metrics": trend_data
                })
        
        # 実行時間が長いエージェントを特定
        slow_agents = [
            (role, trend["average_execution_time"])
            for role, trend in agent_trends.items()
            if trend.get("average_execution_time", 0) > 5.0
        ]
        
        for agent_role, exec_time in slow_agents:
            improvement_areas.append({
                "type": "agent_performance",
                "agent": agent_role,
                "issue": "slow_execution",
                "severity": "medium",
                "metrics": {"average_execution_time": exec_time}
            })
        
        # システム全体の問題を特定
        if system_trend["trend"] == "declining":
            improvement_areas.append({
                "type": "system_performance",
                "issue": "overall_decline",
                "severity": "high",
                "metrics": system_trend
            })
        
        # 学習速度の問題を特定
        recent_insights = self.tracker.get_recent_insights(limit=20)
        if len(recent_insights) < 5:
            improvement_areas.append({
                "type": "learning",
                "issue": "low_learning_rate",
                "severity": "medium",
                "metrics": {"recent_insights_count": len(recent_insights)}
            })
        
        return improvement_areas
    
    def _generate_recommendations(self, improvement_areas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """改善領域に基づいて推奨事項を生成"""
        recommendations = []
        
        for area in improvement_areas:
            if area["type"] == "agent_performance":
                agent = area["agent"]
                issue = area["issue"]
                
                if issue == "performance_decline":
                    recommendations.append({
                        "target": f"config/agents/{agent}.yaml",
                        "action": "update_field",
                        "field": "max_iter",
                        "value": 30,  # 反復回数を増やす
                        "reason": f"{agent}のパフォーマンス低下への対応",
                        "confidence": 0.7
                    })
                    
                    # 知識の追加も推奨
                    recommendations.append({
                        "target": "knowledge",
                        "action": "add",
                        "content": f"{agent}のパフォーマンス改善のための追加ガイドライン",
                        "reason": "エージェント固有の知識強化",
                        "confidence": 0.6
                    })
                
                elif issue == "low_success_rate":
                    recommendations.append({
                        "target": f"config/agents/{agent}.yaml",
                        "action": "update_field",
                        "field": "reasoning",
                        "value": True,  # 推論機能を有効化
                        "reason": f"{agent}の成功率向上のため",
                        "confidence": 0.8
                    })
                
                elif issue == "slow_execution":
                    recommendations.append({
                        "target": f"config/agents/{agent}.yaml",
                        "action": "update_field",
                        "field": "max_iter",
                        "value": 15,  # 反復回数を減らして高速化
                        "reason": f"{agent}の実行速度改善",
                        "confidence": 0.6
                    })
            
            elif area["type"] == "system_performance":
                recommendations.append({
                    "target": "config/crews/main_crew.yaml",
                    "action": "update_field",
                    "field": "planning",
                    "value": True,  # プランニング機能を有効化
                    "reason": "システム全体の調整能力向上",
                    "confidence": 0.7
                })
            
            elif area["type"] == "learning":
                recommendations.append({
                    "target": "knowledge",
                    "action": "analyze_patterns",
                    "reason": "学習パターンの分析と最適化",
                    "confidence": 0.8
                })
        
        # 推奨事項を信頼度でソート
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        
        return recommendations
    
    def apply_adaptations(self, recommendations: List[Dict[str, Any]], 
                         dry_run: bool = True) -> Dict[str, Any]:
        """
        推奨される適応を適用
        
        Args:
            recommendations: 推奨事項のリスト
            dry_run: True の場合はシミュレーションのみ
            
        Returns:
            適用結果
        """
        results = {
            "applied": [],
            "skipped": [],
            "failed": []
        }
        
        for rec in recommendations:
            # 信頼度が閾値以上の場合のみ適用
            if rec["confidence"] >= self.auto_apply_threshold:
                try:
                    if rec["target"] == "knowledge":
                        # 知識グラフへの追加
                        if rec["action"] == "add":
                            node_id = self._add_adaptive_knowledge(rec, dry_run)
                            if node_id:
                                results["applied"].append({
                                    "recommendation": rec,
                                    "result": f"Knowledge node added: {node_id}"
                                })
                        elif rec["action"] == "analyze_patterns":
                            patterns = self._analyze_knowledge_patterns()
                            results["applied"].append({
                                "recommendation": rec,
                                "result": f"Analyzed {len(patterns)} patterns"
                            })
                    else:
                        # 設定ファイルの更新
                        change = [(rec["target"], rec["action"], {
                            "field": rec.get("field"),
                            "value": rec.get("value")
                        })]
                        
                        apply_results = self.applier.apply_changes(change, dry_run)
                        
                        if apply_results["applied"]:
                            results["applied"].append({
                                "recommendation": rec,
                                "result": apply_results["applied"][0]
                            })
                        elif apply_results["failed"]:
                            results["failed"].append({
                                "recommendation": rec,
                                "error": apply_results["failed"][0]
                            })
                        
                except Exception as e:
                    logger.error("Failed to apply adaptation", 
                               recommendation=rec, error=str(e))
                    results["failed"].append({
                        "recommendation": rec,
                        "error": str(e)
                    })
            else:
                results["skipped"].append({
                    "recommendation": rec,
                    "reason": f"信頼度が閾値未満: {rec['confidence']} < {self.auto_apply_threshold}"
                })
        
        # 適応結果を記録
        self._record_adaptation_results(results)
        
        return results
    
    def _add_adaptive_knowledge(self, recommendation: Dict[str, Any], 
                               dry_run: bool) -> Optional[str]:
        """適応的な知識を追加"""
        if dry_run:
            return "dry_run_node_id"
        
        content = recommendation.get("content", "")
        reason = recommendation.get("reason", "")
        
        node = KnowledgeNode(
            id=f"adaptive_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Adaptive Knowledge: {reason}",
            content=content,
            node_type="adaptive",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={
                "source": "adaptive_evolution",
                "confidence": recommendation["confidence"],
                "reason": reason
            }
        )
        
        if self.knowledge_graph.add_knowledge(node):
            return node.id
        
        return None
    
    def _analyze_knowledge_patterns(self) -> List[Dict[str, Any]]:
        """知識パターンを分析"""
        patterns = []
        
        # 最近の成功したタスクから学習
        recent_successes = [
            e for e in self.tracker.evolution_history[-200:]
            if e.get("success", False)
        ]
        
        # エージェント別の成功パターン
        agent_patterns = {}
        for execution in recent_successes:
            agent = execution.get("agent_role", "unknown")
            if agent not in agent_patterns:
                agent_patterns[agent] = []
            agent_patterns[agent].append(execution)
        
        # パターンを抽出
        for agent, executions in agent_patterns.items():
            if len(executions) >= 5:
                # 共通の特徴を探す
                common_features = self._extract_common_features(executions)
                if common_features:
                    patterns.append({
                        "agent": agent,
                        "pattern_type": "success_pattern",
                        "features": common_features,
                        "confidence": len(executions) / 20  # 簡易的な信頼度
                    })
        
        return patterns
    
    def _extract_common_features(self, executions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """実行履歴から共通の特徴を抽出"""
        features = {}
        
        # 実行時間の統計
        exec_times = [e.get("execution_time", 0) for e in executions]
        if exec_times:
            features["avg_execution_time"] = np.mean(exec_times)
            features["std_execution_time"] = np.std(exec_times)
        
        # メタデータから共通要素を探す
        metadata_keys = set()
        for e in executions:
            if "metadata" in e and isinstance(e["metadata"], dict):
                metadata_keys.update(e["metadata"].keys())
        
        if metadata_keys:
            features["common_metadata_keys"] = list(metadata_keys)
        
        return features
    
    def _record_adaptation_results(self, results: Dict[str, Any]):
        """適応結果を記録"""
        adaptation_record = {
            "timestamp": datetime.now().isoformat(),
            "applied_count": len(results["applied"]),
            "skipped_count": len(results["skipped"]),
            "failed_count": len(results["failed"]),
            "details": results
        }
        
        # パフォーマンス履歴に追加
        self.performance_history.append(adaptation_record)
        self.save_performance_history()
        
        # 学習インサイトとして記録
        if results["applied"]:
            self.tracker.record_learning_insight(
                insight_type="adaptation",
                description=f"自動適応を{len(results['applied'])}件適用",
                source="adaptive_evolution_engine",
                impact_score=0.7,
                metadata=adaptation_record
            )
    
    def save_performance_history(self):
        """パフォーマンス履歴を保存"""
        history_file = Path(self.tracker.storage_dir) / "adaptive_performance_history.json"
        with open(history_file, "w") as f:
            json.dump(self.performance_history, f, indent=2)
    
    def load_performance_history(self):
        """パフォーマンス履歴を読み込み"""
        history_file = Path(self.tracker.storage_dir) / "adaptive_performance_history.json"
        if history_file.exists():
            with open(history_file, "r") as f:
                self.performance_history = json.load(f)
        else:
            self.performance_history = []
    
    def get_adaptation_report(self) -> Dict[str, Any]:
        """適応レポートを生成"""
        trends = self.analyze_performance_trends()
        
        if trends["status"] != "analyzed":
            return trends
        
        # 最近の適応履歴
        recent_adaptations = [
            h for h in self.performance_history[-10:]
            if "applied_count" in h
        ]
        
        return {
            "performance_trends": trends,
            "recent_adaptations": recent_adaptations,
            "adaptation_parameters": self.adaptation_params,
            "total_adaptations": sum(
                h.get("applied_count", 0) for h in self.performance_history
            ),
            "success_rate_improvement": self._calculate_improvement_rate()
        }
    
    def _calculate_improvement_rate(self) -> float:
        """改善率を計算"""
        if len(self.performance_history) < 10:
            return 0.0
        
        # 初期と現在のパフォーマンスを比較
        early_perfs = self.performance_history[:5]
        recent_perfs = self.performance_history[-5:]
        
        early_score = np.mean([
            p.get("success_rate", 0) for p in early_perfs
            if "success_rate" in p
        ])
        recent_score = np.mean([
            p.get("success_rate", 0) for p in recent_perfs
            if "success_rate" in p
        ])
        
        if early_score > 0:
            return (recent_score - early_score) / early_score
        
        return 0.0