"""
知識グラフソースのテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from knowledge.knowledge_graph_source import KnowledgeGraphSource


def test_knowledge_graph_source():
    """知識グラフソースをテスト"""
    print("=== 知識グラフソースのテスト ===\n")
    
    # research_agent用の知識を取得
    research_source = KnowledgeGraphSource(agent_role="research_agent", max_related=3)
    research_content = research_source.load_content()
    
    print("Research Agent向け知識:")
    print("-" * 50)
    print(research_content)
    
    print("\n" + "="*60)
    
    # writer_agent用の知識を取得
    writer_source = KnowledgeGraphSource(agent_role="writer_agent", max_related=3)
    writer_content = writer_source.load_content()
    
    print("\nWriter Agent向け知識:")
    print("-" * 50)
    print(writer_content)


if __name__ == "__main__":
    test_knowledge_graph_source()
