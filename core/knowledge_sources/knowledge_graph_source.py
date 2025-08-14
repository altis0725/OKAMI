"""
知識グラフベースの動的知識ソース
CrewAIが知識グラフから関連知識を動的に取得
"""

from typing import List, Dict, Any, Optional
from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource
from core.knowledge_graph import KnowledgeGraphManager


class KnowledgeGraphSource(BaseKnowledgeSource):
    """知識グラフから動的に知識を取得するソース"""
    
    def __init__(self, agent_role: Optional[str] = None, max_related: int = 5, **kwargs):
        # BaseKnowledgeSourceの初期化時に動的コンテンツを渡す
        dynamic_content = self._generate_content(agent_role, max_related)
        super().__init__(content=dynamic_content, **kwargs)
    
    def _generate_content(self, agent_role: Optional[str], max_related: int) -> str:
        """エージェント用の動的コンテンツを生成"""
        if not agent_role:
            return "No agent role specified for knowledge graph source."
        
        kg_manager = KnowledgeGraphManager()
        content_parts = []
        
        # エージェント固有の知識を検索
        search_results = kg_manager.search_knowledge(
            query=agent_role, 
            limit=max_related
        )
        
        if search_results:
            content_parts.append(f"# Knowledge Graph Insights for {agent_role}")
            content_parts.append("")
            
            for result in search_results:
                content_parts.append(f"## {result['title']} ({result['node_type']})")
                content_parts.append(result['content'])
                content_parts.append("")
                
                # 関連知識も取得
                if 'id' in result:
                    related = kg_manager.get_related_knowledge(
                        result['id'], max_depth=1
                    )
                    if related:
                        content_parts.append("### Related Concepts:")
                        for rel in related[:3]:  # 最大3つの関連知識
                            title = rel.get('title', 'Unknown')
                            relation = rel.get('relation_from_source', 'related')
                            content_parts.append(f"- {title} ({relation})")
                        content_parts.append("")
        
        return "\n".join(content_parts) if content_parts else "No relevant knowledge found in graph."
    
    def load_content(self) -> str:
        """すでに初期化時に生成されたコンテンツを返す"""
        return self.content
    
    def add_content_to_knowledge_base(self) -> None:
        """知識ベースに内容を追加（動的ソースなので実装不要）"""
        pass
    
    def add(self) -> None:
        """CrewAI BaseKnowledgeSourceの抽象メソッド実装"""
        # 動的ソースなので何もしない
        pass
    
    def validate_content(self) -> bool:
        """コンテンツの検証"""
        kg_manager = KnowledgeGraphManager()
        return kg_manager.graph.number_of_nodes() > 0
