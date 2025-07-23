"""
Evolution Crew用のコールバック関数
自己適応型進化エンジンと連携して、クルー実行後に自動的に改善を適用
"""

import json
import structlog
from typing import Dict, Any, Optional
from datetime import datetime

from core.adaptive_evolution import AdaptiveEvolutionEngine
from core.evolution_tracker import EvolutionTracker
from core.knowledge_graph import KnowledgeGraphManager
from crewai.crew import CrewOutput
from crewai.task import TaskOutput

logger = structlog.get_logger()


class EvolutionCallback:
    """Evolution Crewのコールバッククラス"""
    
    def __init__(self, 
                 evolution_tracker: Optional[EvolutionTracker] = None,
                 knowledge_graph: Optional[KnowledgeGraphManager] = None,
                 auto_apply: bool = False,
                 confidence_threshold: float = 0.8):
        """
        初期化
        
        Args:
            evolution_tracker: 進化トラッカー
            knowledge_graph: 知識グラフマネージャー
            auto_apply: 自動適用するかどうか
            confidence_threshold: 自動適用の信頼度閾値
        """
        self.evolution_tracker = evolution_tracker or EvolutionTracker()
        self.knowledge_graph = knowledge_graph or KnowledgeGraphManager()
        self.auto_apply = auto_apply
        self.confidence_threshold = confidence_threshold
        
        # AdaptiveEvolutionEngineを初期化
        self.adaptive_engine = AdaptiveEvolutionEngine(
            evolution_tracker=self.evolution_tracker,
            knowledge_graph=self.knowledge_graph,
            auto_apply_threshold=confidence_threshold
        )
        
        logger.info("Evolution callback initialized",
                   auto_apply=auto_apply,
                   confidence_threshold=confidence_threshold)
    
    def on_crew_complete(self, crew_output: CrewOutput) -> CrewOutput:
        """
        クルー実行完了時のコールバック
        
        Args:
            crew_output: クルーの実行結果
            
        Returns:
            処理後のクルー出力
        """
        logger.info("Evolution crew completed, processing results")
        
        try:
            # パフォーマンストレンドを分析
            trends = self.adaptive_engine.analyze_performance_trends()
            
            if trends["status"] == "analyzed":
                logger.info("Performance trends analyzed",
                          system_trend=trends["system_trend"]["trend"],
                          improvement_areas=len(trends["improvement_areas"]))
                
                # 推奨事項を取得
                recommendations = trends["recommendations"]
                
                if recommendations:
                    logger.info(f"Generated {len(recommendations)} recommendations")
                    
                    # 自動適用が有効な場合
                    if self.auto_apply:
                        results = self.adaptive_engine.apply_adaptations(
                            recommendations,
                            dry_run=False
                        )
                        
                        logger.info("Applied adaptations",
                                  applied=len(results["applied"]),
                                  skipped=len(results["skipped"]),
                                  failed=len(results["failed"]))
                        
                        # 結果を知識グラフに記録
                        self._record_to_knowledge_graph(trends, results)
                        
                        # クルー出力に適応結果を追加
                        if crew_output.json_dict is None:
                            crew_output.json_dict = {}
                        
                        crew_output.json_dict["adaptive_evolution"] = {
                            "trends": trends,
                            "adaptations": results,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        # ドライランで結果を確認
                        dry_run_results = self.adaptive_engine.apply_adaptations(
                            recommendations,
                            dry_run=True
                        )
                        
                        logger.info("Dry run completed",
                                  would_apply=len(dry_run_results["applied"]),
                                  would_skip=len(dry_run_results["skipped"]))
                        
                        if crew_output.json_dict is None:
                            crew_output.json_dict = {}
                        
                        crew_output.json_dict["adaptive_evolution"] = {
                            "trends": trends,
                            "dry_run_results": dry_run_results,
                            "auto_apply": False,
                            "timestamp": datetime.now().isoformat()
                        }
                
                # 適応レポートを生成
                report = self.adaptive_engine.get_adaptation_report()
                logger.info("Adaptation report generated",
                          total_adaptations=report.get("total_adaptations", 0),
                          improvement_rate=report.get("success_rate_improvement", 0))
            
            else:
                logger.warning("Insufficient data for analysis",
                             status=trends["status"])
        
        except Exception as e:
            logger.error("Error in evolution callback", error=str(e))
            
            if crew_output.json_dict is None:
                crew_output.json_dict = {}
            
            crew_output.json_dict["adaptive_evolution_error"] = str(e)
        
        return crew_output
    
    def on_task_complete(self, task_output: TaskOutput) -> None:
        """
        タスク完了時のコールバック
        
        Args:
            task_output: タスクの実行結果
        """
        logger.debug("Task completed in evolution crew",
                    task=task_output.description[:50])
        
        # タスクの結果を進化トラッカーに記録
        try:
            self.evolution_tracker.track_task_execution(
                agent_role="evolution_agent",
                task_description=task_output.description,
                execution_time=0.0,  # 実際の実行時間が取得できない場合
                success=True,
                output=task_output.raw,
                metadata={
                    "task_type": "evolution_analysis"
                }
            )
        except Exception as e:
            logger.error("Error tracking task execution", error=str(e))
    
    def _record_to_knowledge_graph(self, trends: Dict[str, Any], 
                                  results: Dict[str, Any]) -> None:
        """
        適応結果を知識グラフに記録
        
        Args:
            trends: パフォーマンストレンド
            results: 適応結果
        """
        try:
            # 適応履歴をノードとして追加
            from core.knowledge_graph import KnowledgeNode
            
            node = KnowledgeNode(
                id=f"adaptation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                title="Adaptive Evolution Result",
                content=json.dumps({
                    "trends": trends,
                    "results": results
                }, indent=2, ensure_ascii=False),
                node_type="adaptation",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={
                    "system_trend": trends["system_trend"]["trend"],
                    "applied_count": len(results["applied"]),
                    "confidence_avg": sum(
                        r["recommendation"]["confidence"] 
                        for r in results["applied"]
                    ) / max(len(results["applied"]), 1)
                }
            )
            
            if self.knowledge_graph.add_knowledge(node):
                logger.info("Adaptation results recorded to knowledge graph",
                          node_id=node.id)
            
            # 成功した適応があれば、関連する知識ノードとリンク
            if results["applied"]:
                from core.knowledge_graph import KnowledgeRelation
                
                for applied in results["applied"]:
                    if "knowledge" in str(applied.get("recommendation", {}).get("target", "")):
                        # 知識関連の適応の場合、関係を追加
                        relation = KnowledgeRelation(
                            source=node.id,
                            target="adaptive_knowledge",
                            relation_type="generated",
                            weight=applied["recommendation"]["confidence"]
                        )
                        self.knowledge_graph.add_relation(relation)
        
        except Exception as e:
            logger.error("Error recording to knowledge graph", error=str(e))


def create_evolution_callback(auto_apply: bool = False,
                            confidence_threshold: float = 0.8) -> EvolutionCallback:
    """
    Evolution Callback のファクトリー関数
    
    Args:
        auto_apply: 自動適用するかどうか
        confidence_threshold: 自動適用の信頼度閾値
        
    Returns:
        EvolutionCallbackインスタンス
    """
    return EvolutionCallback(
        auto_apply=auto_apply,
        confidence_threshold=confidence_threshold
    )


# クルー完了時のコールバック関数（関数形式）
def evolution_crew_callback(crew_output: CrewOutput) -> CrewOutput:
    """
    Evolution Crew完了時のコールバック関数
    
    これは crew_factory で直接使用できる関数形式
    """
    callback = create_evolution_callback(
        auto_apply=False,  # デフォルトはドライラン
        confidence_threshold=0.8
    )
    return callback.on_crew_complete(crew_output)


# タスク完了時のコールバック関数（関数形式）
def evolution_task_callback(task_output: TaskOutput) -> None:
    """
    Evolution タスク完了時のコールバック関数
    """
    callback = create_evolution_callback()
    callback.on_task_complete(task_output)