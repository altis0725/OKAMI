"""
知識管理とグラフメモリの統合層
KnowledgeManagerとGraphMemoryManagerを連携させる
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .knowledge_manager import KnowledgeManager
from .graph_memory_manager import GraphMemoryManager

logger = logging.getLogger(__name__)


class KnowledgeGraphIntegration:
    """
    KnowledgeManagerとGraphMemoryManagerの統合層
    知識とメモリを統合的に管理
    """
    
    def __init__(
        self,
        knowledge_manager: Optional[KnowledgeManager] = None,
        graph_memory: Optional[GraphMemoryManager] = None
    ):
        """
        統合層の初期化
        
        Args:
            knowledge_manager: 知識管理マネージャー
            graph_memory: グラフメモリマネージャー
        """
        self.knowledge_manager = knowledge_manager or KnowledgeManager()
        self.graph_memory = graph_memory or GraphMemoryManager()
        
        logger.info("Knowledge-Graph Integration initialized")
    
    def process_task_result(
        self,
        task_id: str,
        agent_name: str,
        task_description: str,
        result: str,
        success: bool = True
    ) -> Dict[str, Any]:
        """
        タスク結果を処理して知識とメモリに統合
        
        Args:
            task_id: タスクID
            agent_name: エージェント名
            task_description: タスク説明
            result: 実行結果
            success: 成功フラグ
            
        Returns:
            処理結果の詳細
        """
        # メモリグラフに記録
        self.graph_memory.record_task_execution(
            task_id=task_id,
            agent_name=agent_name,
            task_description=task_description,
            result=result,
            success=success
        )
        
        # 成功したタスクから知識を抽出
        if success:
            knowledge_extracted = self._extract_knowledge_from_result(
                agent_name, task_description, result
            )
            
            if knowledge_extracted:
                # 知識とメモリの関連を作成
                self._link_knowledge_to_memory(
                    knowledge_id=knowledge_extracted['id'],
                    task_id=task_id
                )
        
        return {
            'task_id': task_id,
            'memory_recorded': True,
            'knowledge_extracted': success,
            'timestamp': datetime.now().isoformat()
        }
    
    def _extract_knowledge_from_result(
        self,
        agent_name: str,
        task_description: str,
        result: str
    ) -> Optional[Dict[str, Any]]:
        """
        タスク結果から知識を抽出
        
        Args:
            agent_name: エージェント名
            task_description: タスク説明
            result: 実行結果
            
        Returns:
            抽出された知識の情報
        """
        # 知識として価値があるかを判断（簡易版）
        if len(result) < 50:  # 短すぎる結果は知識として保存しない
            return None
        
        # 知識ソースとして追加
        knowledge_content = f"""
## タスク: {task_description}

### 実行エージェント: {agent_name}

### 結果:
{result}

### 学習ポイント:
- このタスクの結果から得られた知見を活用できます
- 類似のタスクで参照可能な情報です
"""
        
        # 知識として保存
        knowledge_source = self.knowledge_manager.create_string_knowledge_source(
            knowledge_content
        )
        
        # メモリグラフにも知識ノードを追加
        knowledge_id = f"knowledge_{task_description[:30]}_{datetime.now().timestamp()}"
        self.graph_memory.add_memory_node(
            node_id=knowledge_id,
            node_type="knowledge",
            content=knowledge_content,
            metadata={
                'agent': agent_name,
                'task': task_description,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        return {'id': knowledge_id, 'source': knowledge_source}
    
    def _link_knowledge_to_memory(self, knowledge_id: str, task_id: str) -> None:
        """
        知識とメモリをリンク
        
        Args:
            knowledge_id: 知識ノードID
            task_id: タスクID
        """
        # タスクから知識への関係を作成
        self.graph_memory.add_memory_relation(
            source_id=f"task_{task_id}",
            target_id=knowledge_id,
            relation_type="learned_from",
            context="タスク実行から得られた知識"
        )
    
    def enhanced_search(
        self,
        query: str,
        search_memory: bool = True,
        search_knowledge: bool = True,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        メモリと知識を横断的に検索
        
        Args:
            query: 検索クエリ
            search_memory: メモリを検索するか
            search_knowledge: 知識を検索するか
            limit: 結果の最大数
            
        Returns:
            統合された検索結果
        """
        results = {
            'query': query,
            'memory_results': [],
            'knowledge_results': [],
            'combined_relevance': []
        }
        
        # メモリグラフから検索
        if search_memory:
            memory_results = self.graph_memory.search_memories(
                query=query,
                limit=limit
            )
            results['memory_results'] = memory_results
            
            # 関連するメモリも取得
            for mem in memory_results[:3]:  # 上位3件の関連を探索
                related = self.graph_memory.find_related_memories(
                    node_id=mem['id'],
                    max_depth=1,
                    limit=5
                )
                mem['related_memories'] = related
        
        # 知識ベースから検索
        if search_knowledge:
            knowledge_results = self.knowledge_manager.search_knowledge(
                query=query,
                limit=limit
            )
            results['knowledge_results'] = knowledge_results
        
        # 結果を統合してランキング
        combined = self._combine_and_rank_results(
            results['memory_results'],
            results['knowledge_results']
        )
        results['combined_relevance'] = combined[:limit]
        
        return results
    
    def _combine_and_rank_results(
        self,
        memory_results: List[Dict],
        knowledge_results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        メモリと知識の検索結果を統合してランキング
        
        Args:
            memory_results: メモリ検索結果
            knowledge_results: 知識検索結果
            
        Returns:
            統合されランキングされた結果
        """
        combined = []
        
        # メモリ結果を追加
        for mem in memory_results:
            combined.append({
                'type': 'memory',
                'content': mem.get('content', ''),
                'score': mem.get('relevance_score', 0) * 1.2,  # メモリを少し優先
                'metadata': mem
            })
        
        # 知識結果を追加
        for know in knowledge_results:
            combined.append({
                'type': 'knowledge',
                'content': know.get('content', ''),
                'score': know.get('score', 0),
                'metadata': know
            })
        
        # スコアでソート
        combined.sort(key=lambda x: x['score'], reverse=True)
        
        return combined
    
    def get_context_for_agent(
        self,
        agent_name: str,
        task_description: str,
        max_items: int = 5
    ) -> Dict[str, Any]:
        """
        エージェントのタスク実行のためのコンテキストを取得
        
        Args:
            agent_name: エージェント名
            task_description: タスク説明
            max_items: 取得する最大アイテム数
            
        Returns:
            エージェント用のコンテキスト情報
        """
        context = {
            'agent': agent_name,
            'task': task_description,
            'relevant_memories': [],
            'relevant_knowledge': [],
            'past_performance': {},
            'suggestions': []
        }
        
        # タスクに関連するメモリを検索
        memory_results = self.graph_memory.search_memories(
            query=task_description,
            limit=max_items
        )
        context['relevant_memories'] = memory_results
        
        # タスクに関連する知識を検索
        knowledge_results = self.knowledge_manager.search_knowledge(
            query=task_description,
            limit=max_items
        )
        context['relevant_knowledge'] = knowledge_results
        
        # エージェントの過去のパフォーマンスを取得
        performance = self.graph_memory.get_agent_performance_history(agent_name)
        context['past_performance'] = performance
        
        # 改善提案を生成
        if performance.get('success_rate', 0) < 0.7:
            context['suggestions'].append(
                "成功率が低いため、タスクの分解や追加リソースの活用を検討してください"
            )
        
        # 知識ギャップを確認
        gaps = self.graph_memory.identify_knowledge_gaps()
        if gaps:
            context['suggestions'].append(
                f"知識ギャップが{len(gaps)}件見つかりました。関連情報の収集を推奨します"
            )
        
        return context
    
    def analyze_system_knowledge_state(self) -> Dict[str, Any]:
        """
        システム全体の知識状態を分析
        
        Returns:
            システムの知識状態分析結果
        """
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'memory_statistics': self.graph_memory.get_graph_statistics(),
            'knowledge_gaps': self.graph_memory.identify_knowledge_gaps(),
            'recommendations': []
        }
        
        # メモリグラフの健全性をチェック
        stats = analysis['memory_statistics']
        
        # 推奨事項を生成
        if stats['total_nodes'] == 0:
            analysis['recommendations'].append(
                "メモリグラフが空です。タスクを実行してメモリを蓄積してください"
            )
        
        if stats.get('connected_components', 0) > 5:
            analysis['recommendations'].append(
                "知識が断片化しています。関連付けを強化することを推奨します"
            )
        
        if stats.get('average_degree', 0) < 2:
            analysis['recommendations'].append(
                "ノード間の接続が少ないです。より多くの関係を見つけることを推奨します"
            )
        
        # 知識ギャップの分析
        gaps = analysis['knowledge_gaps']
        if len(gaps) > 10:
            analysis['recommendations'].append(
                f"{len(gaps)}個の知識ギャップがあります。統合的な学習が必要です"
            )
        
        return analysis
    
    def export_knowledge_graph(self, format: str = "json") -> Dict[str, Any]:
        """
        知識グラフをエクスポート
        
        Args:
            format: エクスポート形式（json, graphml等）
            
        Returns:
            エクスポートされたデータ
        """
        import networkx as nx
        
        if format == "json":
            return nx.node_link_data(self.graph_memory.memory_graph)
        elif format == "graphml":
            # GraphML形式の文字列として返す
            from io import StringIO
            buffer = StringIO()
            nx.write_graphml(self.graph_memory.memory_graph, buffer)
            return {'graphml': buffer.getvalue()}
        else:
            raise ValueError(f"Unsupported format: {format}")