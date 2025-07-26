"""
知識グラフから直接知識を取得するシンプルなテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.knowledge_graph import KnowledgeGraphManager


def test_knowledge_retrieval():
    """知識グラフから知識を取得してCrewAIで利用可能な形式に変換"""
    print("=== 知識グラフからの知識取得テスト ===\n")
    
    kg_manager = KnowledgeGraphManager()
    
    def get_agent_knowledge(agent_role: str) -> str:
        """エージェント用の知識を取得"""
        print(f"{agent_role}用の知識を取得中...")
        
        # エージェント関連の知識を検索
        search_results = kg_manager.search_knowledge(agent_role, limit=5)
        
        if not search_results:
            return f"No knowledge found for {agent_role}"
        
        content_parts = [f"# Enhanced Knowledge for {agent_role}", ""]
        
        for result in search_results:
            content_parts.append(f"## {result['title']}")
            content_parts.append(f"**Type**: {result['node_type']}")
            content_parts.append("")
            content_parts.append(result['content'])
            content_parts.append("")
            
            # メタデータがあれば追加
            if 'metadata' in result:
                metadata = result['metadata']
                if 'priority' in metadata:
                    content_parts.append(f"**Priority**: {metadata['priority']}")
                if 'improvement_type' in metadata:
                    content_parts.append(f"**Type**: {metadata['improvement_type']}")
                content_parts.append("")
        
        return "\n".join(content_parts)
    
    # Research Agent用の知識
    research_knowledge = get_agent_knowledge("research_agent")
    print("Research Agent Knowledge:")
    print("-" * 60)
    print(research_knowledge)
    
    print("\n" + "="*80 + "\n")
    
    # Writer Agent用の知識
    writer_knowledge = get_agent_knowledge("writer_agent")
    print("Writer Agent Knowledge:")
    print("-" * 60)
    print(writer_knowledge)
    
    print("\n" + "="*80 + "\n")
    
    # システム全体の改善知識
    system_knowledge = get_agent_knowledge("system")
    print("System-wide Knowledge:")
    print("-" * 60)
    print(system_knowledge)
    
    print("\n\n=== 知識グラフの統計 ===")
    stats = kg_manager.get_graph_statistics()
    print(f"総ノード数: {stats['node_count']}")
    print(f"改善ノード数: {stats['node_types'].get('improvement', 0)}")
    print(f"基本知識ノード数: {stats['node_count'] - stats['node_types'].get('improvement', 0)}")
    
    print("\n✅ 知識グラフがCrewAIの次回kickoffで活用可能です！")


if __name__ == "__main__":
    test_knowledge_retrieval()