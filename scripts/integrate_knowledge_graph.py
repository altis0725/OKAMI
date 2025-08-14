"""
CrewAIが知識グラフを自動的に活用できるようにする統合スクリプト
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.evolution_tracker import EvolutionTracker
from evolution.improvement_applier import ImprovementApplier
from core.knowledge_graph import KnowledgeGraphManager, KnowledgeNode, KnowledgeRelation


def apply_improvements_to_knowledge_graph():
    """改善提案を知識グラフに自動統合"""
    print("=== 改善提案の知識グラフ統合 ===\n")
    
    # 必要なコンポーネントを初期化
    evolution_dir = project_root / "storage" / "evolution"
    tracker = EvolutionTracker(storage_dir=str(evolution_dir))
    kg_manager = KnowledgeGraphManager()
    applier = ImprovementApplier(base_path=str(project_root))
    
    print(f"現在の知識グラフ状況:")
    print(f"  - ノード数: {kg_manager.graph.number_of_nodes()}")
    print(f"  - エッジ数: {kg_manager.graph.number_of_edges()}\n")
    
    # 改善提案を取得
    suggestions = tracker.get_improvement_suggestions()
    print(f"改善提案数: {len(suggestions)}\n")
    
    if not suggestions:
        print("改善提案がありません。")
        return
    
    # 知識グラフと従来ファイル両方に適用
    changes = []
    knowledge_nodes = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for i, suggestion in enumerate(suggestions):
        print(f"[{suggestion['priority']}] {suggestion['agent_role']}: {suggestion['suggestion']}")
        
        # 1. 従来のファイルベース知識への追加
        content = f"""
## Automated Improvement - {timestamp}

### Identified Issue
{suggestion['suggestion']}

### Recommended Improvements
"""
        for action in suggestion['details']['recommended_actions']:
            content += f"- {action}\n"
        
        if 'recent_failure_tasks' in suggestion['details']:
            content += "\n### Recent Failure Examples\n"
            for task in suggestion['details']['recent_failure_tasks'][:3]:
                content += f"- {task}\n"
        
        # ファイルパスを決定
        if suggestion['agent_role'] == 'system':
            file_path = "knowledge/crew/system_improvements.md"
        else:
            file_path = f"knowledge/agents/{suggestion['agent_role']}.md"
        
        changes.append((file_path, "add", {"content": content}))
        
        # 2. 知識グラフへの追加
        improvement_node = KnowledgeNode(
            id=f"improvement_{suggestion['agent_role']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
            title=f"Performance Improvement: {suggestion['type']}",
            content=suggestion['suggestion'] + "\n\n" + 
                    "Recommended Actions:\n" + 
                    "\n".join(f"- {action}" for action in suggestion['details']['recommended_actions']),
            node_type="improvement",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={
                "agent_role": suggestion['agent_role'],
                "priority": suggestion['priority'],
                "improvement_type": suggestion['type'],
                "source": "evolution_tracker",
                "applied_to_files": True
            }
        )
        knowledge_nodes.append((improvement_node, suggestion))
    
    # ファイルベースの変更を適用
    print(f"\n\nファイルベース知識の更新: {len(changes)}件")
    if changes:
        results = applier.apply_changes(changes, dry_run=False)
        print(f"  - 成功: {len(results['applied'])}件")
        print(f"  - 失敗: {len(results['failed'])}件")
    
    # 知識グラフの更新
    print(f"\n知識グラフの更新: {len(knowledge_nodes)}件")
    for improvement_node, suggestion in knowledge_nodes:
        if kg_manager.add_knowledge(improvement_node):
            print(f"  ✓ {improvement_node.title}")
            
            # 既存のエージェントノードとの関係を作成
            # まず、対応するエージェントノードを検索
            search_results = kg_manager.search_knowledge(suggestion['agent_role'], limit=5)
            
            for result in search_results:
                if result['node_type'] in ['procedure', 'guideline'] and suggestion['agent_role'] in result['title'].lower():
                    # 改善ノードから既存ノードへの関係を作成
                    relation = KnowledgeRelation(
                        source=improvement_node.id,
                        target=result['id'],
                        relation_type="improves",
                        weight=0.9,
                        metadata={
                            "improvement_type": suggestion['type'],
                            "priority": suggestion['priority']
                        }
                    )
                    kg_manager.add_relation(relation)
                    print(f"    → 関係追加: {improvement_node.id} improves {result['id']}")
                    break
    
    # 最終状況
    final_stats = kg_manager.get_graph_statistics()
    print(f"\n\n更新後の知識グラフ:")
    print(f"  - ノード数: {final_stats['node_count']}")
    print(f"  - エッジ数: {final_stats['edge_count']}")
    print(f"  - 改善ノード数: {final_stats['node_types'].get('improvement', 0)}")
    
    print("\n完了！")


def create_knowledge_graph_source():
    """CrewAI用の知識グラフソースを作成"""
    print("\n=== CrewAI知識グラフソースの作成 ===\n")
    
    source_file = project_root / "knowledge" / "knowledge_graph_source.py"
    
    source_code = '''"""
知識グラフベースの動的知識ソース
CrewAIが知識グラフから関連知識を動的に取得
"""

from typing import List, Dict, Any
from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource
from core.knowledge_graph import KnowledgeGraphManager


class KnowledgeGraphSource(BaseKnowledgeSource):
    """知識グラフから動的に知識を取得するソース"""
    
    def __init__(self, agent_role: str = None, max_related: int = 5):
        super().__init__(content="")
        self.agent_role = agent_role
        self.max_related = max_related
        self.kg_manager = KnowledgeGraphManager()
    
    def load_content(self) -> str:
        """エージェントに関連する知識を動的に取得"""
        if not self.agent_role:
            return "No agent role specified for knowledge graph source."
        
        content_parts = []
        
        # エージェント固有の知識を検索
        search_results = self.kg_manager.search_knowledge(
            query=self.agent_role, 
            limit=self.max_related
        )
        
        if search_results:
            content_parts.append(f"# Knowledge Graph Insights for {self.agent_role}")
            content_parts.append("")
            
            for result in search_results:
                content_parts.append(f"## {result['title']} ({result['node_type']})")
                content_parts.append(result['content'])
                content_parts.append("")
                
                # 関連知識も取得
                if 'id' in result:
                    related = self.kg_manager.get_related_knowledge(
                        result['id'], max_depth=1
                    )
                    if related:
                        content_parts.append("### Related Concepts:")
                        for rel in related[:3]:  # 最大3つの関連知識
                            title = rel.get('title', 'Unknown')
                            relation = rel.get('relation_from_source', 'related')
                            content_parts.append(f"- {title} ({relation})")
                        content_parts.append("")
        
        return "\\n".join(content_parts) if content_parts else "No relevant knowledge found in graph."
    
    def add_content_to_knowledge_base(self) -> None:
        """知識ベースに内容を追加（動的ソースなので実装不要）"""
        pass
'''
    
    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(source_code)
    
    print(f"✅ 知識グラフソースを作成: {source_file}")
    
    # テスト用のデモも作成
    demo_file = project_root / "scripts" / "test_knowledge_graph_source.py"
    demo_code = '''"""
知識グラフソースのテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.knowledge_sources.knowledge_graph_source import KnowledgeGraphSource


def test_knowledge_graph_source():
    """知識グラフソースをテスト"""
    print("=== 知識グラフソースのテスト ===\\n")
    
    # research_agent用の知識を取得
    research_source = KnowledgeGraphSource(agent_role="research_agent", max_related=3)
    research_content = research_source.load_content()
    
    print("Research Agent向け知識:")
    print("-" * 50)
    print(research_content)
    
    print("\\n" + "="*60)
    
    # writer_agent用の知識を取得
    writer_source = KnowledgeGraphSource(agent_role="writer_agent", max_related=3)
    writer_content = writer_source.load_content()
    
    print("\\nWriter Agent向け知識:")
    print("-" * 50)
    print(writer_content)


if __name__ == "__main__":
    test_knowledge_graph_source()
'''
    
    with open(demo_file, 'w', encoding='utf-8') as f:
        f.write(demo_code)
    
    print(f"✅ テストスクリプトを作成: {demo_file}")
    
    print("\\n次のステップ:")
    print("1. CrewFactoryでKnowledgeGraphSourceを使用")
    print("2. エージェント作成時に自動的に知識グラフから知識を取得")
    print("3. 改善提案が知識グラフに蓄積され、次回kickoffで活用される")


def main():
    """メイン実行"""
    # 1. 改善提案を知識グラフに統合
    apply_improvements_to_knowledge_graph()
    
    # 2. CrewAI用の知識グラフソースを作成
    create_knowledge_graph_source()


if __name__ == "__main__":
    main()