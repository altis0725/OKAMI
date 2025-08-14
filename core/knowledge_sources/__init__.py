"""
Knowledge Sources for OKAMI System

このモジュールは、CrewAI KnowledgeSourceの各種実装を提供します。
Knowledge Sourceは、エージェントが参照できる知識の動的な取得源です。

Available Sources:
- KnowledgeGraphSource: 知識グラフから動的に知識を取得
- QdrantKnowledgeSource: Qdrantベクトルデータベースを使用（現在無効化）
- StringKnowledgeSourceQdrant: 文字列知識のQdrant保存（現在無効化）
- TextFileKnowledgeSourceQdrant: テキストファイル知識のQdrant保存（現在無効化）
"""

# アクティブなKnowledge Sources
try:
    from .knowledge_graph_source import KnowledgeGraphSource
except ImportError:
    pass

# Qdrant関連（現在無効化されているが、将来の再有効化に備えて保持）
try:
    from .qdrant_knowledge_source import QdrantKnowledgeSource, QdrantKnowledgeStorage
    from .string_knowledge_source_qdrant import StringKnowledgeSourceQdrant
    from .text_file_knowledge_source_qdrant import TextFileKnowledgeSourceQdrant
except ImportError:
    pass

__all__ = [
    "KnowledgeGraphSource",
    "QdrantKnowledgeSource",
    "QdrantKnowledgeStorage",
    "StringKnowledgeSourceQdrant",
    "TextFileKnowledgeSourceQdrant",
]