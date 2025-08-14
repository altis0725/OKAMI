"""
OKAMIシステム用ナレッジマネージャ
クルー全体・エージェント個別の知識管理（RAG対応）
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
import structlog

logger = structlog.get_logger()

# CrewAI標準の知識ソースクラスをインポート
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
from crewai.knowledge.source.csv_knowledge_source import CSVKnowledgeSource
from crewai.knowledge.source.json_knowledge_source import JSONKnowledgeSource
from crewai.knowledge.source.excel_knowledge_source import ExcelKnowledgeSource
from crewai.knowledge.storage.knowledge_storage import KnowledgeStorage
from crewai.knowledge.knowledge_config import KnowledgeConfig
from crewai.utilities.paths import db_storage_path
from datetime import datetime
from .knowledge_graph import KnowledgeGraphManager, KnowledgeNode, KnowledgeRelation


class KnowledgeManager:
    """OKAMIシステムの知識ソースを管理するクラス
    
    CrewAI標準の知識管理機能に準拠し、多様な知識ソースタイプをサポート
    """

    def __init__(
        self,
        knowledge_dir: Optional[str] = None,
        embedder_config: Optional[Dict[str, Any]] = None,
    ):
        """
        ナレッジマネージャの初期化

        Args:
            knowledge_dir: 知識ファイルのディレクトリ
            embedder_config: 埋め込みモデルの設定
        """
        # CrewAIのベストプラクティスに従い、プロジェクトルートのknowledgeフォルダを使用
        self.knowledge_dir = knowledge_dir or os.path.join(os.getcwd(), "knowledge")
        
        # デフォルトでOpenAI embeddingsを使用（CrewAI標準）
        self.embedder_config = embedder_config or {
            "provider": "openai",
            "config": {"model": "text-embedding-3-small"},
        }

        # Ensure knowledge directory exists
        Path(self.knowledge_dir).mkdir(parents=True, exist_ok=True)

        # Knowledge sources registry
        self.crew_sources: List[Any] = []
        self.agent_sources: Dict[str, List[Any]] = {}
        
        # Initialize Knowledge Graph
        self.knowledge_graph = KnowledgeGraphManager()

        # ファイルタイプごとの拡張子マッピング
        self.file_extensions = {
            'text': ['.txt', '.md', '.markdown'],
            'pdf': ['.pdf'],
            'csv': ['.csv'],
            'json': ['.json'],
            'excel': ['.xlsx', '.xls']
        }

        logger.info(
            "Knowledge Manager initialized",
            knowledge_dir=self.knowledge_dir,
            embedder_provider=self.embedder_config.get("provider"),
        )

    def _normalize_knowledge_path(self, file_path: str) -> str:
        """
        CrewAI TextFileKnowledgeSource用にパスを正規化
        パス重複を避けるため、knowledgeディレクトリからの相対パスに変換
        
        Args:
            file_path: 元のファイルパス
            
        Returns:
            正規化されたパス
        """
        path = Path(file_path)
        
        # 絶対パスの場合、knowledgeディレクトリからの相対パスに変換
        if path.is_absolute():
            knowledge_base = Path(self.knowledge_dir).resolve()
            try:
                return str(path.resolve().relative_to(knowledge_base))
            except ValueError:
                # knowledgeディレクトリ外のファイルは警告
                logger.warning(f"File outside knowledge directory: {file_path}")
                return str(path.name)  # ファイル名のみ使用
        
        # "knowledge/"で始まる相対パスは重複を避ける
        path_str = str(path)
        if path_str.startswith("knowledge/"):
            return path_str[10:]  # "knowledge/"を除去
        elif path_str.startswith("./knowledge/"):
            return path_str[12:]  # "./knowledge/"を除去
        
        return path_str

    def create_knowledge_source(self, file_path: str, **kwargs) -> Any:
        """
        ファイルタイプに応じて適切な知識ソースを作成
        
        Args:
            file_path: ファイルパス
            **kwargs: 追加の設定パラメータ
            
        Returns:
            適切な知識ソースインスタンス
        """
        ext = Path(file_path).suffix.lower()
        
        # CrewAI TextFileKnowledgeSourceはknowledgeディレクトリからの相対パスを期待
        # パス重複を避けるために正規化する
        relative_path = self._normalize_knowledge_path(file_path)
        
        # テキストファイル
        if ext in self.file_extensions['text']:
            return TextFileKnowledgeSource(
                file_paths=[relative_path],
                chunk_size=kwargs.get('chunk_size', 1000),
                chunk_overlap=kwargs.get('chunk_overlap', 200)
            )
        # PDFファイル
        elif ext in self.file_extensions['pdf']:
            return PDFKnowledgeSource(
                file_paths=[relative_path]
            )
        # CSVファイル
        elif ext in self.file_extensions['csv']:
            return CSVKnowledgeSource(
                file_paths=[relative_path]
            )
        # JSONファイル
        elif ext in self.file_extensions['json']:
            return JSONKnowledgeSource(
                file_paths=[relative_path]
            )
        # Excelファイル
        elif ext in self.file_extensions['excel']:
            return ExcelKnowledgeSource(
                file_paths=[relative_path]
            )
        else:
            # デフォルトでテキストファイルとして扱う
            logger.warning(f"Unknown file extension {ext}, treating as text file")
            return TextFileKnowledgeSource(
                file_paths=[relative_path],
                chunk_size=kwargs.get('chunk_size', 1000),
                chunk_overlap=kwargs.get('chunk_overlap', 200)
            )
    
    def load_knowledge_from_directory(self, directory: str = None) -> Dict[str, List[Any]]:
        """
        ディレクトリから自動的に知識ファイルを読み込む
        
        Args:
            directory: 読み込むディレクトリ（デフォルトはknowledge_dir）
            
        Returns:
            カテゴリごとの知識ソースの辞書
        """
        directory = directory or self.knowledge_dir
        knowledge_sources = {
            'crew': [],
            'agents': {},
            'domain': [],
            'general': [],
            'system': []
        }
        
        # crewディレクトリの知識を読み込む
        crew_dir = Path(directory) / 'crew'
        if crew_dir.exists():
            for file_path in crew_dir.iterdir():
                if file_path.is_file():
                    source = self.create_knowledge_source(str(file_path))
                    knowledge_sources['crew'].append(source)
                    logger.info(f"Loaded crew knowledge: {file_path.name}")
        
        # agentsディレクトリの知識を読み込む
        agents_dir = Path(directory) / 'agents'
        if agents_dir.exists():
            for file_path in agents_dir.iterdir():
                if file_path.is_file() and file_path.suffix in ['.md', '.txt']:
                    # ファイル名からエージェント名を抽出（例：research_agent.md -> research_agent）
                    agent_name = file_path.stem
                    source = self.create_knowledge_source(str(file_path))
                    
                    if agent_name not in knowledge_sources['agents']:
                        knowledge_sources['agents'][agent_name] = []
                    
                    knowledge_sources['agents'][agent_name].append(source)
                    logger.info(f"Loaded agent knowledge: {agent_name} <- {file_path.name}")
        
        # domainディレクトリの知識を読み込む
        domain_dir = Path(directory) / 'domain'
        if domain_dir.exists():
            for file_path in domain_dir.iterdir():
                if file_path.is_file():
                    source = self.create_knowledge_source(str(file_path))
                    knowledge_sources['domain'].append(source)
                    logger.info(f"Loaded domain knowledge: {file_path.name}")
        
        # generalディレクトリの知識を読み込む
        general_dir = Path(directory) / 'general'
        if general_dir.exists():
            for file_path in general_dir.iterdir():
                if file_path.is_file():
                    source = self.create_knowledge_source(str(file_path))
                    knowledge_sources['general'].append(source)
                    logger.info(f"Loaded general knowledge: {file_path.name}")
        
        # systemディレクトリの知識を読み込む
        system_dir = Path(directory) / 'system'
        if system_dir.exists():
            for file_path in system_dir.iterdir():
                if file_path.is_file():
                    source = self.create_knowledge_source(str(file_path))
                    knowledge_sources['system'].append(source)
                    logger.info(f"Loaded system knowledge: {file_path.name}")
        
        return knowledge_sources

    def add_crew_knowledge(self, source: Any) -> None:
        """
        クルー全体の知識ソースを追加

        Args:
            source: 知識ソース（文字列またはファイル等）
        """
        if isinstance(source, str):
            # 絶対パスの場合はそのまま、相対パスの場合はknowledge_dirと結合
            if os.path.isabs(source):
                full_path = source
            else:
                full_path = os.path.join(self.knowledge_dir, source)
            
            if os.path.exists(full_path):
                knowledge_source = self.create_knowledge_source(full_path)
            else:
                # 文字列コンテンツとして扱う
                knowledge_source = StringKnowledgeSource(
                    content=source,
                    chunk_size=1000,
                    chunk_overlap=200
                )
        else:
            knowledge_source = source

        # 重複チェック
        source_content = str(knowledge_source)
        for existing_source in self.crew_sources:
            if str(existing_source) == source_content:
                logger.debug("Crew knowledge source already exists, skipping", source_type=type(knowledge_source).__name__)
                return

        self.crew_sources.append(knowledge_source)
        logger.info("Crew knowledge source added", source_type=type(knowledge_source).__name__)

    def add_agent_knowledge(self, agent_role: str, source: Any) -> None:
        """
        エージェント個別の知識ソースを追加

        Args:
            agent_role: エージェントの役割名
            source: 知識ソース
        """
        if agent_role not in self.agent_sources:
            self.agent_sources[agent_role] = []

        if isinstance(source, str):
            # 絶対パスの場合はそのまま、相対パスの場合はknowledge_dirと結合
            if os.path.isabs(source):
                full_path = source
            else:
                full_path = os.path.join(self.knowledge_dir, source)
            
            if os.path.exists(full_path):
                knowledge_source = self.create_knowledge_source(full_path)
            else:
                # 文字列コンテンツとして扱う
                knowledge_source = StringKnowledgeSource(
                    content=source,
                    chunk_size=1000,
                    chunk_overlap=200
                )
        else:
            knowledge_source = source

        # 重複チェック
        source_content = str(knowledge_source)
        for existing_source in self.agent_sources[agent_role]:
            if str(existing_source) == source_content:
                logger.debug("Agent knowledge source already exists, skipping", 
                           agent_role=agent_role, source_type=type(knowledge_source).__name__)
                return

        self.agent_sources[agent_role].append(knowledge_source)
        logger.info(
            "Agent knowledge source added",
            agent_role=agent_role,
            source_type=type(knowledge_source).__name__,
        )

    def get_crew_knowledge_config(self) -> Dict[str, Any]:
        """クルー全体の知識設定を取得"""
        if not self.crew_sources:
            return {}

        return {
            "knowledge_sources": self.crew_sources,
            "embedder": self.embedder_config,
        }

    def get_agent_knowledge_config(
        self, agent_role: str, knowledge_config: Optional[KnowledgeConfig] = None
    ) -> Dict[str, Any]:
        """
        エージェント個別の知識設定を取得

        Args:
            agent_role: エージェントの役割
            knowledge_config: オプションの知識取得設定

        Returns:
            知識設定の辞書
        """
        sources = self.agent_sources.get(agent_role, [])
        if not sources:
            return {}

        config = {
            "knowledge_sources": sources,
            "embedder": self.embedder_config,
        }

        if knowledge_config:
            config["knowledge_config"] = knowledge_config

        return config

    def create_custom_storage(
        self, collection_name: str, embedder_config: Optional[Dict] = None
    ) -> KnowledgeStorage:
        """
        カスタム知識ストレージを作成

        Args:
            collection_name: コレクション名
            embedder_config: 埋め込み設定

        Returns:
            KnowledgeStorageインスタンス
        """
        return KnowledgeStorage(
            embedder=embedder_config or self.embedder_config,
            collection_name=collection_name,
        )

    def list_collections(self) -> List[str]:
        """全知識コレクション名をリストで返す"""
        # CrewAI標準の知識ストレージパスから情報を取得
        try:
            storage_path = db_storage_path()
            knowledge_path = os.path.join(storage_path, "knowledge")
            
            if os.path.exists(knowledge_path):
                collections = [d for d in os.listdir(knowledge_path) 
                             if os.path.isdir(os.path.join(knowledge_path, d))]
                return collections
            else:
                return []
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        コレクション情報を取得

        Args:
            collection_name: コレクション名

        Returns:
            コレクション情報
        """
        # 基本的な情報のみ返す
        return {
            'name': collection_name,
            'exists': collection_name in self.list_collections(),
            'storage_path': os.path.join(db_storage_path(), "knowledge", collection_name)
        }

    def reset_knowledge(self, knowledge_type: str = "all") -> None:
        """
        知識をリセット

        Args:
            knowledge_type: リセット対象（'crew', 'agent', 'all'）
        """
        try:
            if knowledge_type in ["crew", "all"]:
                self.crew_sources.clear()

            if knowledge_type in ["agent", "all"]:
                self.agent_sources.clear()

            logger.info("Knowledge reset completed", knowledge_type=knowledge_type)
        except Exception as e:
            logger.error(f"Failed to reset knowledge: {e}", knowledge_type=knowledge_type)
    
    def add_knowledge_to_graph(self, title: str, content: str, 
                              node_type: str = "general",
                              metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        知識グラフに知識を追加
        
        Args:
            title: 知識のタイトル
            content: 知識の内容
            node_type: ノードタイプ（concept, fact, procedure, example等）
            metadata: メタデータ
        
        Returns:
            作成されたノードID（失敗時はNone）
        """
        try:
            # ノードIDを生成
            node_id = f"{node_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(title) % 10000}"
            
            # 知識ノードを作成
            node = KnowledgeNode(
                id=node_id,
                title=title,
                content=content,
                node_type=node_type,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata=metadata or {}
            )
            
            # グラフに追加
            if self.knowledge_graph.add_knowledge(node):
                logger.info("Knowledge added to graph", node_id=node_id, title=title)
                return node_id
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to add knowledge to graph: {e}")
            return None
    
    def add_knowledge_relation(self, source_id: str, target_id: str, 
                              relation_type: str = "related_to",
                              weight: float = 1.0) -> bool:
        """
        知識間の関係を追加
        
        Args:
            source_id: ソースノードID
            target_id: ターゲットノードID
            relation_type: 関係タイプ（is_a, part_of, related_to, depends_on等）
            weight: 関係の重み
        
        Returns:
            成功したかどうか
        """
        try:
            relation = KnowledgeRelation(
                source=source_id,
                target=target_id,
                relation_type=relation_type,
                weight=weight
            )
            
            return self.knowledge_graph.add_relation(relation)
            
        except Exception as e:
            logger.error(f"Failed to add knowledge relation: {e}")
            return False
    
    def search_knowledge_graph(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        知識グラフから検索
        
        Args:
            query: 検索クエリ
            limit: 結果の最大数
        
        Returns:
            マッチする知識のリスト
        """
        return self.knowledge_graph.search_knowledge(query, limit)
    
    def get_related_knowledge_from_graph(self, node_id: str, 
                                       relation_types: Optional[List[str]] = None,
                                       max_depth: int = 2) -> List[Dict[str, Any]]:
        """
        グラフから関連知識を取得
        
        Args:
            node_id: 起点ノードID
            relation_types: フィルタする関係タイプ
            max_depth: 探索の最大深度
        
        Returns:
            関連する知識のリスト
        """
        return self.knowledge_graph.get_related_knowledge(node_id, relation_types, max_depth)
    
    def get_knowledge_graph_stats(self) -> Dict[str, Any]:
        """
        知識グラフの統計情報を取得
        
        Returns:
            統計情報
        """
        return self.knowledge_graph.get_graph_statistics()
    
    def refresh_knowledge_from_directory(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        ディレクトリから知識を動的に更新
        
        Args:
            force_reload: 強制的に再読み込みするかどうか
            
        Returns:
            更新結果の統計
        """
        try:
            logger.info("Starting knowledge refresh", force_reload=force_reload)
            
            # 現在の知識をバックアップ（必要に応じて）
            if force_reload:
                self.reset_knowledge("all")
            
            # 自動読み込みを実行
            knowledge_sources = self.load_knowledge_from_directory()
            
            # クルー知識を追加（crew + domain + general + system をクルー全体で共有）
            crew_added = 0
            
            # crewディレクトリ
            for source in knowledge_sources['crew']:
                # 重複チェック
                source_content = str(source)
                if not any(str(existing) == source_content for existing in self.crew_sources):
                    self.crew_sources.append(source)
                    crew_added += 1
                    logger.info("Crew knowledge source added", source_type=type(source).__name__)
            
            # domainディレクトリ（クルー全体で共有）
            for source in knowledge_sources['domain']:
                source_content = str(source)
                if not any(str(existing) == source_content for existing in self.crew_sources):
                    self.crew_sources.append(source)
                    crew_added += 1
                    logger.info("Domain knowledge added to crew", source_type=type(source).__name__)
            
            # generalディレクトリ（クルー全体で共有）
            for source in knowledge_sources['general']:
                source_content = str(source)
                if not any(str(existing) == source_content for existing in self.crew_sources):
                    self.crew_sources.append(source)
                    crew_added += 1
                    logger.info("General knowledge added to crew", source_type=type(source).__name__)
            
            # systemディレクトリ（クルー全体で共有）
            for source in knowledge_sources['system']:
                source_content = str(source)
                if not any(str(existing) == source_content for existing in self.crew_sources):
                    self.crew_sources.append(source)
                    crew_added += 1
                    logger.info("System knowledge added to crew", source_type=type(source).__name__)
            
            # エージェント知識を追加（すでに知識ソースオブジェクト）
            agent_added = 0
            for agent_name, sources in knowledge_sources['agents'].items():
                if agent_name not in self.agent_sources:
                    self.agent_sources[agent_name] = []
                
                for source in sources:
                    # 重複チェック
                    source_content = str(source)
                    if not any(str(existing) == source_content for existing in self.agent_sources[agent_name]):
                        self.agent_sources[agent_name].append(source)
                        agent_added += 1
                        logger.info("Agent knowledge source added", agent_role=agent_name, source_type=type(source).__name__)
            
            # 統計情報を作成
            stats = {
                "crew_knowledge_added": crew_added,
                "agent_knowledge_added": agent_added,
                "total_crew_sources": len(self.crew_sources),
                "total_agent_sources": sum(len(sources) for sources in self.agent_sources.values()),
                "agents_with_knowledge": list(self.agent_sources.keys()),
                "domain_sources": len(knowledge_sources['domain']),
                "general_sources": len(knowledge_sources['general']),
                "system_sources": len(knowledge_sources['system']),
                "refresh_timestamp": datetime.now().isoformat()
            }
            
            logger.info("Knowledge refresh completed", **stats)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to refresh knowledge: {e}")
            return {"error": str(e), "success": False}
    
    def auto_initialize_knowledge(self) -> bool:
        """
        システム起動時に知識を自動初期化
        
        Returns:
            初期化が成功したかどうか
        """
        try:
            logger.info("Starting automatic knowledge initialization")
            
            # ディレクトリ構造を確認・作成
            agents_dir = Path(self.knowledge_dir) / 'agents'
            crew_dir = Path(self.knowledge_dir) / 'crew'
            domain_dir = Path(self.knowledge_dir) / 'domain'
            general_dir = Path(self.knowledge_dir) / 'general'
            system_dir = Path(self.knowledge_dir) / 'system'
            
            agents_dir.mkdir(parents=True, exist_ok=True)
            crew_dir.mkdir(parents=True, exist_ok=True)
            domain_dir.mkdir(parents=True, exist_ok=True)
            general_dir.mkdir(parents=True, exist_ok=True)
            system_dir.mkdir(parents=True, exist_ok=True)
            
            # デフォルト知識ファイルが存在しない場合は作成
            self._create_default_knowledge_files()
            
            # 知識を読み込み
            stats = self.refresh_knowledge_from_directory()
            
            logger.info("Automatic knowledge initialization completed", stats=stats)
            return stats.get("error") is None
            
        except Exception as e:
            logger.error(f"Failed to auto-initialize knowledge: {e}")
            return False
    
    def _create_default_knowledge_files(self):
        """デフォルトの知識ファイルを作成"""
        agents_dir = Path(self.knowledge_dir) / 'agents'
        crew_dir = Path(self.knowledge_dir) / 'crew'
        
        # デフォルトクルー知識
        default_crew_knowledge = """# OKAMI System Best Practices

## Collaboration Guidelines
- Always maintain clear communication between agents
- Share relevant findings with team members
- Ask for clarification when task requirements are unclear
- Provide detailed context when delegating tasks

## Quality Standards
- Verify information from multiple sources when possible
- Document assumptions and limitations
- Use structured formats for consistent output
- Include confidence levels for recommendations

## Error Handling
- Report errors clearly with specific details
- Suggest alternative approaches when primary methods fail
- Learn from failures to improve future performance
"""
        
        crew_knowledge_file = crew_dir / "best_practices.md"
        if not crew_knowledge_file.exists():
            crew_knowledge_file.write_text(default_crew_knowledge, encoding='utf-8')
            logger.info(f"Created default crew knowledge: {crew_knowledge_file}")
        
        # デフォルトエージェント知識（research_agent用）
        default_research_knowledge = """# Research Agent Guidelines

## Research Methodology
- Use multiple sources to verify information
- Prioritize recent and authoritative sources
- Document source credibility and bias
- Provide citations and references

## Information Gathering
- Start with broad searches, then narrow down
- Use specific keywords and search operators
- Cross-reference findings across sources
- Note any conflicting information

## Output Format
- Begin with executive summary
- Provide detailed findings with sources
- Include methodology and limitations
- Suggest areas for further investigation
"""
        
        research_agent_file = agents_dir / "research_agent.md"
        if not research_agent_file.exists():
            research_agent_file.write_text(default_research_knowledge, encoding='utf-8')
            logger.info(f"Created default research agent knowledge: {research_agent_file}")
    
    def watch_knowledge_directory(self, callback=None):
        """
        知識ディレクトリの変更を監視（将来の機能）
        
        Args:
            callback: ファイル変更時に呼び出されるコールバック関数
        """
        # 将来的にwatchdogライブラリなどを使用してファイル変更を監視
        # 現在は手動更新のみサポート
        logger.info("Knowledge directory watching not yet implemented")
        pass