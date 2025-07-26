"""
知識グラフ機能のデモスクリプト
NetworkXを使用した知識の構造化と関係性管理のデモ
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.knowledge_graph import KnowledgeGraphManager, KnowledgeNode, KnowledgeRelation
from core.knowledge_manager import KnowledgeManager
from core.evolution_tracker import EvolutionTracker


def main():
    """メイン実行"""
    print("=== 知識グラフ機能デモ ===\n")
    
    # 知識グラフマネージャーの初期化
    kg_manager = KnowledgeGraphManager()
    
    print(f"初期状態:")
    print(f"  - ノード数: {kg_manager.graph.number_of_nodes()}")
    print(f"  - エッジ数: {kg_manager.graph.number_of_edges()}\n")
    
    # ステップ1: 基本的な知識ノードを追加
    print("ステップ1: 基本知識の追加")
    print("-" * 50)
    
    # エージェントに関する知識
    nodes = [
        KnowledgeNode(
            id="agent_research_001",
            title="Research Agent Best Practices",
            content="Research agents should verify information from multiple sources and provide citations.",
            node_type="procedure",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"agent": "research_agent", "category": "best_practice"}
        ),
        KnowledgeNode(
            id="agent_writer_001",
            title="Writer Agent Guidelines",
            content="Writer agents should structure content clearly and use appropriate language for the target audience.",
            node_type="procedure",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"agent": "writer_agent", "category": "guideline"}
        ),
        KnowledgeNode(
            id="concept_crew_001",
            title="Crew Collaboration Concept",
            content="Crews work best when agents have complementary skills and clear communication protocols.",
            node_type="concept",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"scope": "crew", "category": "concept"}
        ),
        KnowledgeNode(
            id="fact_performance_001",
            title="Performance Optimization Facts",
            content="Tasks taking over 30 seconds often indicate inefficient tool usage or overly broad task descriptions.",
            node_type="fact",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"category": "performance", "threshold": 30}
        )
    ]
    
    for node in nodes:
        success = kg_manager.add_knowledge(node)
        print(f"  ✓ {node.title} - {'成功' if success else '失敗'}")
    
    # ステップ2: 知識間の関係を追加
    print("\n\nステップ2: 知識間の関係を定義")
    print("-" * 50)
    
    relations = [
        KnowledgeRelation(
            source="agent_research_001",
            target="concept_crew_001",
            relation_type="contributes_to",
            weight=0.8,
            metadata={"description": "Research quality contributes to crew success"}
        ),
        KnowledgeRelation(
            source="agent_writer_001",
            target="concept_crew_001",
            relation_type="contributes_to",
            weight=0.8,
            metadata={"description": "Clear writing contributes to crew communication"}
        ),
        KnowledgeRelation(
            source="fact_performance_001",
            target="agent_research_001",
            relation_type="applies_to",
            weight=0.9,
            metadata={"description": "Performance facts apply to research tasks"}
        ),
        KnowledgeRelation(
            source="fact_performance_001",
            target="agent_writer_001",
            relation_type="applies_to",
            weight=0.9,
            metadata={"description": "Performance facts apply to writing tasks"}
        )
    ]
    
    for relation in relations:
        success = kg_manager.add_relation(relation)
        print(f"  ✓ {relation.source} → {relation.target} ({relation.relation_type})")
    
    # ステップ3: 改善提案から知識を生成
    print("\n\nステップ3: 改善提案を知識グラフに統合")
    print("-" * 50)
    
    # EvolutionTrackerから改善提案を取得
    evolution_dir = project_root / "storage" / "evolution"
    tracker = EvolutionTracker(storage_dir=str(evolution_dir))
    suggestions = tracker.get_improvement_suggestions()
    
    print(f"改善提案数: {len(suggestions)}\n")
    
    for i, suggestion in enumerate(suggestions[:3]):  # 最初の3つを処理
        # 改善提案を知識ノードとして追加
        improvement_node = KnowledgeNode(
            id=f"improvement_{suggestion['agent_role']}_{i:03d}",
            title=f"Improvement for {suggestion['agent_role']}",
            content=suggestion['suggestion'] + "\n\nActions:\n" + 
                    "\n".join(f"- {action}" for action in suggestion['details']['recommended_actions']),
            node_type="improvement",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={
                "agent_role": suggestion['agent_role'],
                "priority": suggestion['priority'],
                "type": suggestion['type']
            }
        )
        
        if kg_manager.add_knowledge(improvement_node):
            print(f"  ✓ 改善提案を追加: {improvement_node.title}")
            
            # 関連するエージェントノードとの関係を作成
            if suggestion['agent_role'] == 'research_agent':
                kg_manager.add_relation(KnowledgeRelation(
                    source=improvement_node.id,
                    target="agent_research_001",
                    relation_type="improves",
                    weight=0.95
                ))
            elif suggestion['agent_role'] == 'writer_agent':
                kg_manager.add_relation(KnowledgeRelation(
                    source=improvement_node.id,
                    target="agent_writer_001",
                    relation_type="improves",
                    weight=0.95
                ))
    
    # ステップ4: 知識検索のデモ
    print("\n\nステップ4: 知識グラフの検索")
    print("-" * 50)
    
    # キーワード検索
    search_results = kg_manager.search_knowledge("agent", limit=5)
    print(f"\n'agent'を含む知識: {len(search_results)}件")
    for result in search_results:
        print(f"  - [{result['node_type']}] {result['title']}")
    
    # 関連知識の取得
    print("\n\nResearch Agentに関連する知識:")
    related = kg_manager.get_related_knowledge("agent_research_001", max_depth=2)
    for i, knowledge in enumerate(related):
        # node_dataから情報を取得
        title = knowledge.get('title', 'No title')
        relation = knowledge.get('relation_from_source', 'unknown')
        distance = knowledge.get('distance', 0)
        print(f"  - [{distance}] {title} (関係: {relation})")
    
    # ステップ5: グラフの統計情報
    print("\n\nステップ5: 知識グラフの統計")
    print("-" * 50)
    
    stats = kg_manager.get_graph_statistics()
    print(f"総ノード数: {stats['node_count']}")
    print(f"総エッジ数: {stats['edge_count']}")
    print(f"弱連結成分数: {stats['connected_components']}")
    print(f"\nノードタイプ別:")
    for node_type, count in stats['node_types'].items():
        print(f"  - {node_type}: {count}")
    print(f"\n関係タイプ別:")
    for rel_type, count in stats['relation_types'].items():
        print(f"  - {rel_type}: {count}")
    
    # グラフの保存確認
    graph_file = Path(kg_manager.storage_path) / "knowledge_graph.json"
    if graph_file.exists():
        print(f"\n\n✅ 知識グラフが保存されました: {graph_file}")
        print(f"   ファイルサイズ: {graph_file.stat().st_size} bytes")
    
    print("\n完了！")


if __name__ == "__main__":
    main()