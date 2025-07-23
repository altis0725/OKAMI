"""
Knowledge Graph Module

NetworkXを使用した知識グラフの実装。
知識間の関係性を管理し、効率的な知識検索を提供。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

import networkx as nx
from pydantic import BaseModel

from utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeNode(BaseModel):
    """知識ノードのモデル"""
    id: str
    title: str
    content: str
    node_type: str  # concept, fact, procedure, example, etc.
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}
    file_path: Optional[str] = None


class KnowledgeRelation(BaseModel):
    """知識間の関係のモデル"""
    source: str
    target: str
    relation_type: str  # is_a, part_of, related_to, depends_on, etc.
    weight: float = 1.0
    metadata: Dict[str, Any] = {}


class KnowledgeGraphManager:
    """
    NetworkXベースの知識グラフマネージャー
    
    知識の構造化と関係性管理を提供
    """
    
    def __init__(self, storage_path: str = "storage/knowledge_graph"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.graph = nx.DiGraph()
        self.load_graph()
        
        # 知識ファイルの保存パス
        self.knowledge_path = self.storage_path / "knowledge_files"
        self.knowledge_path.mkdir(exist_ok=True)
        
        logger.info("Knowledge graph initialized", 
                   node_count=self.graph.number_of_nodes(),
                   edge_count=self.graph.number_of_edges())
    
    def add_knowledge(self, node: KnowledgeNode) -> bool:
        """
        知識ノードを追加
        
        Args:
            node: 追加する知識ノード
            
        Returns:
            成功したかどうか
        """
        try:
            # MDファイルに知識を保存
            file_path = self._save_knowledge_file(node)
            node.file_path = str(file_path)
            
            # グラフにノードを追加
            self.graph.add_node(
                node.id,
                title=node.title,
                content=node.content,
                node_type=node.node_type,
                created_at=node.created_at.isoformat(),
                updated_at=node.updated_at.isoformat(),
                metadata=node.metadata,
                file_path=node.file_path
            )
            
            self.save_graph()
            logger.info("Knowledge node added", node_id=node.id, title=node.title)
            return True
            
        except Exception as e:
            logger.error("Failed to add knowledge node", error=str(e))
            return False
    
    def add_relation(self, relation: KnowledgeRelation) -> bool:
        """
        知識間の関係を追加
        
        Args:
            relation: 追加する関係
            
        Returns:
            成功したかどうか
        """
        try:
            # 両方のノードが存在することを確認
            if relation.source not in self.graph:
                logger.warning("Source node not found", node_id=relation.source)
                return False
            if relation.target not in self.graph:
                logger.warning("Target node not found", node_id=relation.target)
                return False
            
            # エッジを追加
            self.graph.add_edge(
                relation.source,
                relation.target,
                relation_type=relation.relation_type,
                weight=relation.weight,
                metadata=relation.metadata
            )
            
            self.save_graph()
            logger.info("Relation added", 
                       source=relation.source, 
                       target=relation.target,
                       type=relation.relation_type)
            return True
            
        except Exception as e:
            logger.error("Failed to add relation", error=str(e))
            return False
    
    def get_related_knowledge(self, node_id: str, 
                            relation_types: Optional[List[str]] = None,
                            max_depth: int = 2) -> List[Dict[str, Any]]:
        """
        関連する知識を取得
        
        Args:
            node_id: 起点となるノードID
            relation_types: フィルタする関係タイプ（Noneの場合すべて）
            max_depth: 探索の最大深度
            
        Returns:
            関連する知識のリスト
        """
        if node_id not in self.graph:
            logger.warning("Node not found", node_id=node_id)
            return []
        
        related_nodes = []
        visited = set()
        
        def explore(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            # 出力エッジを探索
            for neighbor in self.graph.successors(current_id):
                edge_data = self.graph[current_id][neighbor]
                
                # 関係タイプのフィルタリング
                if relation_types and edge_data.get('relation_type') not in relation_types:
                    continue
                
                if neighbor not in visited:
                    node_data = self.graph.nodes[neighbor].copy()
                    node_data['distance'] = depth
                    node_data['relation_from_source'] = edge_data.get('relation_type')
                    related_nodes.append(node_data)
                    
                    # 再帰的に探索
                    explore(neighbor, depth + 1)
        
        explore(node_id, 1)
        
        # 距離でソート
        related_nodes.sort(key=lambda x: x['distance'])
        
        return related_nodes
    
    def find_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """
        2つの知識間の最短経路を見つける
        
        Args:
            source_id: 開始ノードID
            target_id: 目標ノードID
            
        Returns:
            経路のノードIDリスト（見つからない場合はNone）
        """
        try:
            path = nx.shortest_path(self.graph, source_id, target_id)
            return path
        except nx.NetworkXNoPath:
            logger.info("No path found", source=source_id, target=target_id)
            return None
        except nx.NodeNotFound:
            logger.warning("Node not found in path search", 
                         source=source_id, target=target_id)
            return None
    
    def get_knowledge_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """
        タイプ別に知識を取得
        
        Args:
            node_type: ノードタイプ
            
        Returns:
            該当する知識のリスト
        """
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get('node_type') == node_type:
                node_data = data.copy()
                node_data['id'] = node_id
                nodes.append(node_data)
        
        return nodes
    
    def get_knowledge_content(self, node_id: str) -> Optional[str]:
        """
        知識の完全なコンテンツを取得
        
        Args:
            node_id: ノードID
            
        Returns:
            知識の内容（見つからない場合はNone）
        """
        if node_id not in self.graph:
            return None
        
        node_data = self.graph.nodes[node_id]
        file_path = node_data.get('file_path')
        
        if file_path and Path(file_path).exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error("Failed to read knowledge file", 
                           file_path=file_path, error=str(e))
        
        # ファイルが見つからない場合はノードのコンテンツを返す
        return node_data.get('content', '')
    
    def update_knowledge(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        知識ノードを更新
        
        Args:
            node_id: 更新するノードID
            updates: 更新内容
            
        Returns:
            成功したかどうか
        """
        if node_id not in self.graph:
            logger.warning("Node not found for update", node_id=node_id)
            return False
        
        try:
            # ノードデータを更新
            node_data = self.graph.nodes[node_id]
            node_data.update(updates)
            node_data['updated_at'] = datetime.now().isoformat()
            
            # コンテンツが更新された場合はファイルも更新
            if 'content' in updates and node_data.get('file_path'):
                self._update_knowledge_file(node_id, updates['content'])
            
            self.save_graph()
            logger.info("Knowledge node updated", node_id=node_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update knowledge node", error=str(e))
            return False
    
    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        キーワードで知識を検索
        
        Args:
            query: 検索クエリ
            limit: 結果の最大数
            
        Returns:
            マッチする知識のリスト
        """
        query_lower = query.lower()
        results = []
        
        for node_id, data in self.graph.nodes(data=True):
            # タイトルとコンテンツで検索
            title = data.get('title', '').lower()
            content = data.get('content', '').lower()
            
            if query_lower in title or query_lower in content:
                score = 0
                if query_lower in title:
                    score += 2  # タイトルマッチは高スコア
                if query_lower in content:
                    score += 1
                
                result = data.copy()
                result['id'] = node_id
                result['search_score'] = score
                results.append(result)
        
        # スコアでソート
        results.sort(key=lambda x: x['search_score'], reverse=True)
        
        return results[:limit]
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        グラフの統計情報を取得
        
        Returns:
            統計情報
        """
        stats = {
            'node_count': self.graph.number_of_nodes(),
            'edge_count': self.graph.number_of_edges(),
            'node_types': {},
            'relation_types': {},
            'connected_components': nx.number_weakly_connected_components(self.graph),
            'average_degree': 0
        }
        
        # ノードタイプの集計
        for _, data in self.graph.nodes(data=True):
            node_type = data.get('node_type', 'unknown')
            stats['node_types'][node_type] = stats['node_types'].get(node_type, 0) + 1
        
        # 関係タイプの集計
        for _, _, data in self.graph.edges(data=True):
            rel_type = data.get('relation_type', 'unknown')
            stats['relation_types'][rel_type] = stats['relation_types'].get(rel_type, 0) + 1
        
        # 平均次数
        if stats['node_count'] > 0:
            stats['average_degree'] = sum(dict(self.graph.degree()).values()) / stats['node_count']
        
        return stats
    
    def _save_knowledge_file(self, node: KnowledgeNode) -> Path:
        """
        知識をMDファイルとして保存
        
        Args:
            node: 保存する知識ノード
            
        Returns:
            保存したファイルのパス
        """
        # ファイル名を生成（IDをベースに）
        file_name = f"{node.id}.md"
        file_path = self.knowledge_path / file_name
        
        # MDファイルの内容を生成
        content = f"""# {node.title}

**Type**: {node.node_type}  
**Created**: {node.created_at.strftime('%Y-%m-%d %H:%M:%S')}  
**Updated**: {node.updated_at.strftime('%Y-%m-%d %H:%M:%S')}  

## Content

{node.content}

## Metadata

```json
{json.dumps(node.metadata, indent=2, ensure_ascii=False)}
```
"""
        
        # ファイルに書き込み
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def _update_knowledge_file(self, node_id: str, new_content: str) -> bool:
        """
        知識ファイルの内容を更新
        
        Args:
            node_id: ノードID
            new_content: 新しいコンテンツ
            
        Returns:
            成功したかどうか
        """
        node_data = self.graph.nodes[node_id]
        file_path = node_data.get('file_path')
        
        if not file_path or not Path(file_path).exists():
            logger.warning("Knowledge file not found", node_id=node_id)
            return False
        
        try:
            # 既存のファイルを読み込んで更新
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # コンテンツセクションを更新
            in_content = False
            new_lines = []
            
            for line in lines:
                if line.strip() == "## Content":
                    new_lines.append(line)
                    new_lines.append("\n")
                    new_lines.append(new_content)
                    new_lines.append("\n\n")
                    in_content = True
                elif line.strip() == "## Metadata" and in_content:
                    in_content = False
                    new_lines.append(line)
                elif not in_content:
                    new_lines.append(line)
            
            # ファイルに書き込み
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            return True
            
        except Exception as e:
            logger.error("Failed to update knowledge file", error=str(e))
            return False
    
    def save_graph(self):
        """グラフをファイルに保存"""
        graph_file = self.storage_path / "knowledge_graph.json"
        
        try:
            # NetworkXのグラフをJSON形式で保存
            data = nx.node_link_data(self.graph)
            with open(graph_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug("Knowledge graph saved", file=str(graph_file))
            
        except Exception as e:
            logger.error("Failed to save knowledge graph", error=str(e))
    
    def load_graph(self):
        """グラフをファイルから読み込み"""
        graph_file = self.storage_path / "knowledge_graph.json"
        
        if not graph_file.exists():
            logger.info("No existing knowledge graph found, starting with empty graph")
            return
        
        try:
            with open(graph_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.graph = nx.node_link_graph(data)
            logger.info("Knowledge graph loaded", 
                       nodes=self.graph.number_of_nodes(),
                       edges=self.graph.number_of_edges())
            
        except Exception as e:
            logger.error("Failed to load knowledge graph", error=str(e))
            self.graph = nx.DiGraph()