"""
グラフベースのメモリ管理システム
CrewAIのメモリシステムに知識グラフ機能を統合
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import networkx as nx
from crewai import Crew, Agent, Task

logger = logging.getLogger(__name__)


class GraphMemoryManager:
    """
    OKAMIシステム用の知識グラフメモリ管理
    メモリ（会話履歴、タスク結果、学習内容）を知識グラフとして構造化
    """
    
    def __init__(self, storage_path: str = "storage/graph_memory"):
        """
        グラフメモリマネージャーの初期化
        
        Args:
            storage_path: グラフメモリの保存パス
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # メモリグラフの初期化
        self.memory_graph = nx.DiGraph()
        self.load_memory_graph()
        
        # エンティティタイプの定義
        self.entity_types = {
            "agent": "エージェント",
            "task": "タスク",
            "user": "ユーザー",
            "concept": "概念",
            "skill": "スキル",
            "result": "実行結果",
            "error": "エラー",
            "improvement": "改善点"
        }
        
        # 関係タイプの定義
        self.relation_types = {
            "executed": "実行した",
            "learned_from": "から学習した",
            "depends_on": "に依存する",
            "similar_to": "に類似する",
            "improves": "を改善する",
            "caused_by": "が原因",
            "uses": "を使用する",
            "mentions": "に言及する"
        }
        
        logger.info(
            f"Graph Memory Manager initialized - nodes: {self.memory_graph.number_of_nodes()}, edges: {self.memory_graph.number_of_edges()}"
        )
    
    def get_memory_config(self) -> Dict[str, Any]:
        """
        CrewAI用のメモリ設定を返す
        
        Returns:
            メモリ設定辞書
        """
        # CrewAIの標準メモリにグラフメモリを追加
        return {
            "provider": "basic",  # CrewAIの基本プロバイダーを使用
            "storage": {
                "type": "graph",
                "path": str(self.storage_path),
                "graph_backend": "networkx"
            }
        }
    
    def add_memory_node(
        self,
        node_id: str,
        node_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        メモリノードを追加
        
        Args:
            node_id: ノードの一意識別子
            node_type: ノードタイプ（agent, task, user, concept等）
            content: ノードの内容
            metadata: 追加のメタデータ
            
        Returns:
            追加に成功したかどうか
        """
        try:
            self.memory_graph.add_node(
                node_id,
                node_type=node_type,
                content=content,
                created_at=datetime.now().isoformat(),
                metadata=metadata or {},
                access_count=0
            )
            
            self.save_memory_graph()
            logger.debug(f"Memory node added: {node_id} ({node_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add memory node: {e}")
            return False
    
    def add_memory_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        context: Optional[str] = None,
        weight: float = 1.0
    ) -> bool:
        """
        メモリノード間の関係を追加
        
        Args:
            source_id: ソースノードID
            target_id: ターゲットノードID
            relation_type: 関係タイプ
            context: 関係のコンテキスト
            weight: 関係の重み
            
        Returns:
            追加に成功したかどうか
        """
        try:
            # ノードが存在することを確認
            if source_id not in self.memory_graph:
                logger.warning(f"Source node not found: {source_id}")
                return False
            if target_id not in self.memory_graph:
                logger.warning(f"Target node not found: {target_id}")
                return False
            
            self.memory_graph.add_edge(
                source_id,
                target_id,
                relation_type=relation_type,
                context=context,
                weight=weight,
                created_at=datetime.now().isoformat()
            )
            
            self.save_memory_graph()
            logger.debug(
                f"Memory relation added: {source_id} -{relation_type}-> {target_id}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to add memory relation: {e}")
            return False
    
    def record_task_execution(
        self,
        task_id: str,
        agent_name: str,
        task_description: str,
        result: str,
        success: bool = True
    ) -> None:
        """
        タスク実行をグラフに記録
        
        Args:
            task_id: タスクID
            agent_name: 実行したエージェント名
            task_description: タスク説明
            result: 実行結果
            success: 成功したかどうか
        """
        # タスクノードを追加
        self.add_memory_node(
            node_id=f"task_{task_id}",
            node_type="task",
            content=task_description,
            metadata={"success": success, "timestamp": datetime.now().isoformat()}
        )
        
        # エージェントノードを追加（存在しない場合）
        agent_id = f"agent_{agent_name}"
        if agent_id not in self.memory_graph:
            self.add_memory_node(
                node_id=agent_id,
                node_type="agent",
                content=f"Agent: {agent_name}",
                metadata={"name": agent_name}
            )
        
        # 結果ノードを追加
        result_id = f"result_{task_id}"
        self.add_memory_node(
            node_id=result_id,
            node_type="result",
            content=result,
            metadata={"success": success}
        )
        
        # 関係を追加
        self.add_memory_relation(agent_id, f"task_{task_id}", "executed")
        self.add_memory_relation(f"task_{task_id}", result_id, "produced")
        
        # エンティティと概念を抽出して関係を作成
        self._extract_and_link_entities(task_description, f"task_{task_id}")
        self._extract_and_link_entities(result, result_id)
    
    def _extract_and_link_entities(self, text: str, source_node_id: str) -> None:
        """
        テキストからエンティティを抽出してリンク
        
        Args:
            text: 解析するテキスト
            source_node_id: ソースノードID
        """
        # 簡単なエンティティ抽出（実際の実装では NLP を使用）
        # ここでは重要そうなキーワードを抽出
        keywords = [
            word.strip() 
            for word in text.split() 
            if len(word.strip()) > 4 and word[0].isupper()
        ]
        
        for keyword in keywords[:5]:  # 最大5個のキーワード
            concept_id = f"concept_{keyword.lower()}"
            
            # 概念ノードを追加（存在しない場合）
            if concept_id not in self.memory_graph:
                self.add_memory_node(
                    node_id=concept_id,
                    node_type="concept",
                    content=keyword,
                    metadata={"keyword": keyword}
                )
            
            # 関係を追加
            self.add_memory_relation(source_node_id, concept_id, "mentions")
    
    def find_related_memories(
        self,
        node_id: str,
        relation_types: Optional[List[str]] = None,
        max_depth: int = 2,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        関連するメモリを検索
        
        Args:
            node_id: 起点となるノードID
            relation_types: フィルタする関係タイプ
            max_depth: 探索の最大深度
            limit: 返す結果の最大数
            
        Returns:
            関連メモリのリスト
        """
        if node_id not in self.memory_graph:
            logger.warning(f"Node not found: {node_id}")
            return []
        
        related_memories = []
        visited = set()
        
        def explore(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            # 出力エッジを探索
            for neighbor in self.memory_graph.successors(current_id):
                if neighbor in visited:
                    continue
                    
                edge_data = self.memory_graph[current_id][neighbor]
                
                # 関係タイプのフィルタリング
                if relation_types and edge_data.get('relation_type') not in relation_types:
                    continue
                
                node_data = self.memory_graph.nodes[neighbor].copy()
                node_data['id'] = neighbor
                node_data['distance'] = depth
                node_data['relation'] = edge_data.get('relation_type')
                related_memories.append(node_data)
                
                # 再帰的に探索
                explore(neighbor, depth + 1)
        
        explore(node_id, 1)
        
        # 距離でソートして制限
        related_memories.sort(key=lambda x: x['distance'])
        return related_memories[:limit]
    
    def search_memories(
        self,
        query: str,
        node_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        メモリを検索
        
        Args:
            query: 検索クエリ
            node_types: フィルタするノードタイプ
            limit: 返す結果の最大数
            
        Returns:
            マッチしたメモリのリスト
        """
        query_lower = query.lower()
        results = []
        
        for node_id, data in self.memory_graph.nodes(data=True):
            # ノードタイプのフィルタリング
            if node_types and data.get('node_type') not in node_types:
                continue
            
            # コンテンツで検索
            content = data.get('content', '').lower()
            if query_lower in content:
                result = data.copy()
                result['id'] = node_id
                result['relevance_score'] = content.count(query_lower)
                results.append(result)
        
        # 関連度でソート
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:limit]
    
    def get_agent_performance_history(self, agent_name: str) -> Dict[str, Any]:
        """
        エージェントのパフォーマンス履歴を取得
        
        Args:
            agent_name: エージェント名
            
        Returns:
            パフォーマンス統計
        """
        agent_id = f"agent_{agent_name}"
        
        if agent_id not in self.memory_graph:
            return {"error": "Agent not found"}
        
        # エージェントが実行したタスクを取得
        executed_tasks = []
        for neighbor in self.memory_graph.successors(agent_id):
            edge_data = self.memory_graph[agent_id][neighbor]
            if edge_data.get('relation_type') == 'executed':
                task_data = self.memory_graph.nodes[neighbor]
                executed_tasks.append({
                    'task_id': neighbor,
                    'success': task_data.get('metadata', {}).get('success', False),
                    'timestamp': task_data.get('metadata', {}).get('timestamp')
                })
        
        # 統計を計算
        total_tasks = len(executed_tasks)
        successful_tasks = sum(1 for t in executed_tasks if t['success'])
        
        return {
            'agent_name': agent_name,
            'total_tasks': total_tasks,
            'successful_tasks': successful_tasks,
            'success_rate': successful_tasks / total_tasks if total_tasks > 0 else 0,
            'recent_tasks': executed_tasks[-5:]  # 最近の5タスク
        }
    
    def identify_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """
        知識のギャップを特定
        
        Returns:
            ギャップのリスト
        """
        gaps = []
        
        # 孤立したノードを探す
        isolated_nodes = list(nx.isolates(self.memory_graph))
        for node_id in isolated_nodes:
            node_data = self.memory_graph.nodes[node_id]
            gaps.append({
                'type': 'isolated_knowledge',
                'node_id': node_id,
                'content': node_data.get('content', ''),
                'suggestion': 'このノードを他の知識と関連付ける必要があります'
            })
        
        # 弱い接続を持つコンポーネントを探す
        components = list(nx.weakly_connected_components(self.memory_graph))
        small_components = [c for c in components if len(c) < 3]
        
        for component in small_components:
            gaps.append({
                'type': 'weak_connection',
                'nodes': list(component),
                'suggestion': 'これらのノード群をより大きな知識ネットワークに統合する必要があります'
            })
        
        return gaps
    
    def save_memory_graph(self) -> None:
        """メモリグラフを保存"""
        graph_file = self.storage_path / "memory_graph.json"
        
        try:
            data = nx.node_link_data(self.memory_graph)
            with open(graph_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Memory graph saved to {graph_file}")
            
        except Exception as e:
            logger.error(f"Failed to save memory graph: {e}")
    
    def load_memory_graph(self) -> None:
        """メモリグラフを読み込み"""
        graph_file = self.storage_path / "memory_graph.json"
        
        if not graph_file.exists():
            logger.info("No existing memory graph found, starting with empty graph")
            return
        
        try:
            with open(graph_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.memory_graph = nx.node_link_graph(data)
            logger.info(
                f"Memory graph loaded: {self.memory_graph.number_of_nodes()} nodes, "
                f"{self.memory_graph.number_of_edges()} edges"
            )
            
        except Exception as e:
            logger.error(f"Failed to load memory graph: {e}")
            self.memory_graph = nx.DiGraph()
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        グラフの統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        stats = {
            'total_nodes': self.memory_graph.number_of_nodes(),
            'total_edges': self.memory_graph.number_of_edges(),
            'node_types': {},
            'relation_types': {},
            'connected_components': nx.number_weakly_connected_components(self.memory_graph),
            'average_degree': 0
        }
        
        # ノードタイプの集計
        for _, data in self.memory_graph.nodes(data=True):
            node_type = data.get('node_type', 'unknown')
            stats['node_types'][node_type] = stats['node_types'].get(node_type, 0) + 1
        
        # 関係タイプの集計
        for _, _, data in self.memory_graph.edges(data=True):
            rel_type = data.get('relation_type', 'unknown')
            stats['relation_types'][rel_type] = stats['relation_types'].get(rel_type, 0) + 1
        
        # 平均次数
        if stats['total_nodes'] > 0:
            degrees = dict(self.memory_graph.degree())
            stats['average_degree'] = sum(degrees.values()) / stats['total_nodes']
        
        return stats