#!/usr/bin/env python3
"""
Qdrantに知識ベースを初期化するスクリプト
ChromaDB依存を避けるため、直接Qdrantに知識を登録する
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.vector_store import get_vector_store
from tools.knowledge_search_tool import add_knowledge_to_base
import ollama

def load_knowledge_files():
    """知識ファイルを読み込む"""
    knowledge_data = []
    knowledge_dir = project_root / "knowledge"
    
    # OKAMIシステムの概要
    okami_overview = """
# OKAMIシステム概要

OKAMI（Orchestrated Knowledge-driven Autonomous Multi-agent Intelligence）は、CrewAIフレームワークをベースに構築された自己成長型AIエージェントシステムです。

## 主な特徴

1. **マルチエージェント協調**: 複数のAIエージェントが協調して作業を行う
2. **自己成長機能**: 経験から学習し、知識を蓄積・共有することで時間とともに進化
3. **階層型タスク管理**: マネージャーエージェントがタスクを適切に分配
4. **知識ベース統合**: Qdrantベクトルデータベースを使用した高度な知識管理
5. **品質保証機能**: ガードレールによる出力の品質検証

## システムアーキテクチャ

- **コアフレームワーク**: CrewAI
- **ベクトルストア**: Qdrant
- **LLMプロバイダー**: Monica API (GPT-4o互換)
- **エンベディング**: Ollama (mxbai-embed-large)
- **メモリ管理**: Mem0

## 主要コンポーネント

1. **エージェント群**
   - Research Agent: 調査・情報収集
   - Analysis Agent: データ分析
   - Writer Agent: 文書作成
   - Validator Agent: 品質検証
   - Manager Agent: タスク管理・分配

2. **知識管理システム**
   - KnowledgeManager: 知識の統合管理
   - Vector Store: ベクトル検索対応
   - Knowledge Graph: 知識間の関係管理

3. **進化システム**
   - Evolution Tracker: 進化の追跡
   - Improvement Applier: 改善の自動適用
   - Adaptive Evolution: 自己適応機能
"""
    knowledge_data.append({
        "content": okami_overview,
        "metadata": {"source": "system", "category": "overview", "title": "OKAMI System Overview"}
    })
    
    # エージェント用の知識を読み込む
    agents_dir = knowledge_dir / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            try:
                content = agent_file.read_text(encoding="utf-8")
                if content.strip():
                    knowledge_data.append({
                        "content": content,
                        "metadata": {
                            "source": "agent",
                            "agent": agent_file.stem,
                            "category": "agent_knowledge",
                            "file": str(agent_file.name)
                        }
                    })
                    print(f"Loaded agent knowledge: {agent_file.name}")
            except Exception as e:
                print(f"Error loading {agent_file}: {e}")
    
    # CrewAI用の知識を読み込む
    crew_dir = knowledge_dir / "crew"
    if crew_dir.exists():
        for crew_file in crew_dir.glob("*.md"):
            try:
                content = crew_file.read_text(encoding="utf-8")
                if content.strip():
                    knowledge_data.append({
                        "content": content,
                        "metadata": {
                            "source": "crew",
                            "category": "crew_knowledge",
                            "file": str(crew_file.name)
                        }
                    })
                    print(f"Loaded crew knowledge: {crew_file.name}")
            except Exception as e:
                print(f"Error loading {crew_file}: {e}")
    
    return knowledge_data

def initialize_qdrant_knowledge():
    """Qdrantに知識を初期化"""
    raise NotImplementedError("Qdrantは無効化されています")

if __name__ == "__main__":
    print("Qdrantは無効化されています")