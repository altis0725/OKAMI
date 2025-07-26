"""
QdrantベースのTextFileKnowledgeSource
テキストファイルからの知識をQdrantに保存
"""

from typing import List, Dict, Any, Optional
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from knowledge.qdrant_knowledge_source import QdrantKnowledgeStorage
from core.embedding_manager import get_embedding_manager
from pathlib import Path
import structlog

logger = structlog.get_logger()


class TextFileKnowledgeSourceQdrant:
    """Qdrantを使用するTextFileKnowledgeSource"""
    
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Qdrantは無効化されています")
    
    def validate_content(self) -> Dict[str, str]:
        """ファイルの内容を読み込んで検証"""
        contents = {}
        
        for file_path in self.file_paths:
            path = Path(file_path)
            
            # ファイルの存在確認
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            
            # ファイルがテキストファイルか確認
            if not path.is_file():
                logger.warning(f"Not a file: {file_path}")
                continue
            
            try:
                # ファイルを読み込む
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():  # 空でないことを確認
                        contents[str(path)] = content
                    else:
                        logger.warning(f"Empty file: {file_path}")
                        
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
        
        if not contents:
            raise ValueError("No valid text files found")
        
        return contents
    
    def add(self) -> None:
        """ファイルの内容を処理してQdrantに保存"""
        try:
            # ファイルの内容を検証して読み込む
            file_contents = self.validate_content()
            
            all_chunks = []
            all_metadatas = []
            
            # 各ファイルの内容を処理
            for file_path, content in file_contents.items():
                # テキストをチャンクに分割
                chunks = self._chunk_text(content)
                
                # メタデータを各チャンクに追加
                for i, chunk in enumerate(chunks):
                    chunk_metadata = {
                        "source": "text_file",
                        "file_path": file_path,
                        "file_name": Path(file_path).name,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        **self.metadata  # ユーザー定義のメタデータを含める
                    }
                    all_chunks.append(chunk)
                    all_metadatas.append(chunk_metadata)
            
            # Qdrantストレージに保存
            if all_chunks:
                self.storage.save(all_chunks, metadata=all_metadatas)
                logger.info(f"Successfully added {len(all_chunks)} chunks from {len(file_contents)} files to Qdrant")
            else:
                logger.warning("No chunks to save")
            
        except Exception as e:
            logger.error(f"Failed to add text file knowledge to Qdrant: {e}")
            raise


def create_qdrant_text_file_source(*args, **kwargs):
    """Qdrantベースのテキストファイル知識ソースを作成するヘルパー関数"""
    raise NotImplementedError("Qdrantは無効化されています")