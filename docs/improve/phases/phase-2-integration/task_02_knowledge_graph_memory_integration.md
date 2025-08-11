# タスク2: 知識グラフのCrewAIメモリシステム統合

## タスク概要

**目標**: 現在のOKAMIメモリ機能に知識グラフを統合し、より効果的な知識管理と検索を実現する  
**優先度**: 高  
**予想作業時間**: 3-4時間  
**担当者**: AI Assistant  
**前提条件**: タスク1（general.md構造化）完了

## 現状分析

### 現在のOKAMIメモリ構成
```python
# core/memory_manager.py
class MemoryManager:
    - CrewAI標準メモリ（basic provider）
    - SQLiteベースの永続化
    - Mem0外部メモリシステム（オプション）
```

### CrewAIメモリ機能の現状（2025年1月最新）
#### サポートされるメモリタイプ
1. **Short-term Memory**: ChromaDB + RAGによる一時的情報保存
2. **Long-term Memory**: SQLite3による永続的学習内容保存
3. **Entity Memory**: RAGによる特定エンティティ情報整理

#### 知識グラフサポート状況
- **ネイティブ機能**: まだ完全な知識グラフサポートなし
- **Mem0統合**: Graph Memory機能が利用可能
- **カスタム実装**: External Memoryによる独自実装が可能

### 統合の課題
- 現在のKnowledgeManagerとの競合回避
- CrewAI標準メモリとの適切な役割分担
- パフォーマンスとスケーラビリティの確保
- 既存エージェントとの互換性維持

## 実装戦略

### 戦略1: Mem0 Graph Memory統合（推奨）
**利点**: 
- CrewAI公式サポート
- 自動エンティティ関係推論
- マルチモーダル対応

**実装アプローチ**:
```python
# core/graph_memory_manager.py
class GraphMemoryManager:
    def __init__(self):
        self.mem0_config = {
            "provider": "mem0",
            "config": {
                "user_id": "okami_system",
                "custom_categories": self._get_okami_categories(),
                "infer": True  # 自動関係推論
            }
        }
```

### 戦略2: カスタムグラフストレージ実装
**利点**:
- OKAMI特化の最適化
- 完全な制御
- ChromaDBとの統合

**実装アプローチ**:
```python
# core/knowledge_graph_storage.py
class KnowledgeGraphStorage(Storage):
    def __init__(self):
        self.graph = nx.DiGraph()
        self.chroma_client = chromadb.PersistentClient()
```

## 実装手順

### Step 1: Mem0統合アプローチの実装

#### 1.1 依存関係の追加
```bash
# requirements.txtに追加
mem0ai>=1.0.0
networkx>=3.0
```

#### 1.2 GraphMemoryManagerの作成
```python
# core/graph_memory_manager.py
import os
from typing import Dict, List, Any, Optional
from crewai import Crew
from crewai.memory.external.external_memory import ExternalMemory
import logging

class GraphMemoryManager:
    """
    OKAMIシステム用の知識グラフメモリ管理
    Mem0のGraph Memory機能を活用
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        self.user_id = "okami_system"
        self.org_id = "okami_org"
        self.project_id = "okami_project"
        
        if not self.api_key:
            logging.warning("MEM0_API_KEY not found. Graph memory will use basic fallback.")
    
    def get_memory_config(self) -> Dict[str, Any]:
        """CrewAI用のメモリ設定を返す"""
        if self.api_key:
            return {
                "provider": "mem0",
                "config": {
                    "user_id": self.user_id,
                    "org_id": self.org_id,
                    "project_id": self.project_id,
                    "api_key": self.api_key,
                    "custom_categories": self._get_okami_categories(),
                    "infer": True,  # 自動関係推論
                    "includes": "entities,relationships,insights",
                    "excludes": "temporary_data"
                }
            }
        else:
            # フォールバック: 基本メモリ
            return {"provider": "basic"}
    
    def _get_okami_categories(self) -> List[Dict[str, str]]:
        """OKAMI特化のカテゴリ定義"""
        return [
            {
                "system_components": "OKAMIシステムのコンポーネント、モジュール、設定に関する情報"
            },
            {
                "agent_knowledge": "各エージェントの専門知識、能力、実行履歴"
            },
            {
                "task_patterns": "タスクパターン、成功事例、失敗パターンの関係"
            },
            {
                "domain_expertise": "特定ドメインの知識とその相互関係"
            },
            {
                "evolution_insights": "システム進化に関する洞察と改善パターン"
            },
            {
                "user_interactions": "ユーザーとの対話パターンと好み"
            }
        ]
    
    def create_crew_with_graph_memory(self, agents: List, tasks: List, **crew_kwargs) -> Crew:
        """グラフメモリを統合したCrewを作成"""
        memory_config = self.get_memory_config()
        
        return Crew(
            agents=agents,
            tasks=tasks,
            memory=True,
            memory_config=memory_config,
            embedder=self._get_embedder_config(),
            **crew_kwargs
        )
    
    def _get_embedder_config(self) -> Dict[str, Any]:
        """OKAMI用のエンベッダー設定"""
        # Monica LLMと同じプロバイダーを使用
        return {
            "provider": "openai",  # Monica LLMのOpenAI互換APIを活用
            "config": {
                "api_key": os.getenv("MONICA_API_KEY"),
                "base_url": os.getenv("MONICA_BASE_URL"),
                "model": "text-embedding-3-small"
            }
        }
    
    def add_entity_relationship(self, entity1: str, relationship: str, entity2: str, 
                              context: str = "", metadata: Dict = None):
        """
        エンティティ間の関係を明示的に追加
        Mem0のGraph Memory機能を活用
        """
        relationship_text = f"{entity1} {relationship} {entity2}"
        if context:
            relationship_text += f" - {context}"
        
        # この情報はMem0に保存され、自動的にグラフ構造化される
        return {
            "content": relationship_text,
            "metadata": {
                "type": "relationship",
                "entity1": entity1,
                "relationship": relationship,
                "entity2": entity2,
                "context": context,
                **(metadata or {})
            }
        }
```

#### 1.3 既存MemoryManagerとの統合
```python
# core/memory_manager.py（更新）
from .graph_memory_manager import GraphMemoryManager

class MemoryManager:
    def __init__(self):
        # 既存の機能
        self.basic_provider_config = {"provider": "basic"}
        
        # 新規: グラフメモリ統合
        self.graph_memory = GraphMemoryManager()
        
    def get_enhanced_memory_config(self, use_graph_memory: bool = True) -> Dict[str, Any]:
        """拡張されたメモリ設定を取得"""
        if use_graph_memory:
            return self.graph_memory.get_memory_config()
        else:
            return self.basic_provider_config
            
    def create_crew_with_memory(self, agents: List, tasks: List, 
                               use_graph_memory: bool = True, **kwargs) -> Crew:
        """メモリ統合されたCrewを作成"""
        if use_graph_memory:
            return self.graph_memory.create_crew_with_graph_memory(
                agents, tasks, **kwargs
            )
        else:
            return Crew(
                agents=agents,
                tasks=tasks,
                memory=True,
                memory_config=self.basic_provider_config,
                **kwargs
            )
```

### Step 2: KnowledgeManagerとの統合

#### 2.1 KnowledgeGraphIntegration
```python
# core/knowledge_graph_integration.py
from typing import Dict, List, Any
from .knowledge_manager import KnowledgeManager
from .graph_memory_manager import GraphMemoryManager

class KnowledgeGraphIntegration:
    """
    KnowledgeManagerとGraphMemoryManagerの統合層
    """
    
    def __init__(self, knowledge_manager: KnowledgeManager, 
                 graph_memory: GraphMemoryManager):
        self.knowledge_manager = knowledge_manager
        self.graph_memory = graph_memory
        
    def add_structured_knowledge(self, knowledge_content: str, 
                                entities: List[str] = None,
                                relationships: List[Dict] = None):
        """構造化された知識を両システムに同期"""
        
        # 1. 従来のベクトル検索用知識として追加
        knowledge_source = self.knowledge_manager.create_string_knowledge_source(
            knowledge_content
        )
        
        # 2. エンティティと関係をグラフメモリに追加
        if entities:
            for entity in entities:
                entity_info = self.graph_memory.add_entity_relationship(
                    entity, "defined_in", "knowledge_base",
                    context=knowledge_content[:200] + "..."
                )
        
        if relationships:
            for rel in relationships:
                self.graph_memory.add_entity_relationship(
                    rel["from"], rel["relationship"], rel["to"],
                    context=rel.get("context", ""),
                    metadata={"source": "knowledge_integration"}
                )
        
        return knowledge_source
    
    def enhanced_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """ベクトル検索とグラフ検索を組み合わせた拡張検索"""
        
        # 1. 従来のベクトル検索
        vector_results = self.knowledge_manager.search_knowledge(
            query, limit=limit
        )
        
        # 2. グラフベースの関連情報取得（Mem0の機能を活用）
        # 注: Mem0のGraph Memoryは自動的に関連エンティティを提供
        
        return {
            "vector_results": vector_results,
            "query": query,
            "enhanced_context": "Graph memory integration provides deeper context"
        }
```

### Step 3: CrewFactoryの更新

#### 3.1 グラフメモリ対応の追加
```python
# crews/crew_factory.py（更新部分）
from core.graph_memory_manager import GraphMemoryManager
from core.knowledge_graph_integration import KnowledgeGraphIntegration

class CrewFactory:
    def __init__(self):
        # 既存の初期化
        self.memory_manager = MemoryManager()
        self.knowledge_manager = KnowledgeManager()
        self.guardrail_manager = GuardrailManager()
        
        # 新規: グラフメモリとの統合
        self.graph_memory = GraphMemoryManager()
        self.kg_integration = KnowledgeGraphIntegration(
            self.knowledge_manager, self.graph_memory
        )
    
    def create_crew(self, crew_config: Dict[str, Any]) -> Crew:
        """グラフメモリ対応のCrew作成"""
        
        # グラフメモリの使用可否を設定から判定
        use_graph_memory = crew_config.get("graph_memory", True)
        
        if use_graph_memory:
            # グラフメモリ統合版
            crew = self.graph_memory.create_crew_with_graph_memory(
                agents=agents,
                tasks=tasks,
                process=process_type,
                knowledge_sources=enhanced_knowledge,
                planning=crew_config.get("planning", False),
                planning_llm=planning_llm
            )
        else:
            # 従来版（後方互換性）
            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=process_type,
                memory=True,
                memory_config=self.memory_manager.get_memory_config(),
                knowledge_sources=knowledge_sources
            )
        
        return crew
```

### Step 4: 設定ファイルの更新

#### 4.1 環境変数の追加
```bash
# .env
# 既存設定...

# Mem0 Graph Memory設定（オプション）
MEM0_API_KEY=m0-your-api-key-here

# グラフメモリ機能の有効/無効
ENABLE_GRAPH_MEMORY=true
```

#### 4.2 CrewAI設定の更新
```yaml
# config/crews/main_crew.yaml（更新部分）
memory: true
graph_memory: true  # 新規設定

# メモリ設定（基本設定は後方互換性のために保持）
memory_config:
  provider: "basic"  # フォールバック用

# 知識グラフ固有設定
knowledge_graph:
  auto_extract_entities: true
  relationship_inference: true
  custom_categories:
    - system_components
    - agent_knowledge
    - task_patterns
```

### Step 5: 段階的マイグレーション戦略

#### 5.1 フェーズA: 共存期間（既存機能を保持）
```python
# 設定による切り替え
USE_GRAPH_MEMORY = os.getenv("ENABLE_GRAPH_MEMORY", "false").lower() == "true"

if USE_GRAPH_MEMORY:
    memory_config = graph_memory_manager.get_memory_config()
else:
    memory_config = {"provider": "basic"}
```

#### 5.2 フェーズB: 段階的移行
- 新しいタスクではグラフメモリを使用
- 既存のタスクは従来メモリを使用
- 徐々にデータ移行

#### 5.3 フェーズC: 完全移行
- すべてのCrewでグラフメモリを使用
- 従来メモリは非推奨化

## 実装チェックリスト

### Phase 1: 基盤実装
- [ ] GraphMemoryManagerクラスの作成
- [ ] Mem0統合設定の実装
- [ ] 環境変数とフォールバック機能の実装
- [ ] 基本的なエンティティ・関係管理機能

### Phase 2: 統合実装
- [ ] 既存MemoryManagerとの統合
- [ ] KnowledgeManagerとの連携実装
- [ ] CrewFactoryの更新
- [ ] 設定ファイルの更新

### Phase 3: テストと検証
- [ ] 基本機能のユニットテスト
- [ ] エンドツーエンドの統合テスト
- [ ] パフォーマンステスト
- [ ] 後方互換性の確認

### Phase 4: ドキュメント更新
- [ ] CLAUDE.mdの更新
- [ ] general.mdへの機能説明追加
- [ ] 使用例とベストプラクティスの文書化

## 検証方法

### 機能テスト
```bash
# 1. 基本的なグラフメモリ機能テスト
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "crew_name": "main_crew",
    "task": "John は Software Engineer です。彼はAI技術に興味があります。この情報を記憶し、後で関連する質問に答えられるようにしてください。",
    "async_execution": false
  }'

# 2. エンティティ関係の検索テスト
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "crew_name": "main_crew", 
    "task": "John について知っていることと、AI技術との関係を教えてください",
    "async_execution": false
  }'

# 3. 複雑な関係推論テスト
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "crew_name": "main_crew",
    "task": "Software Engineer として働く人が AI技術 に興味を持つ場合、どのような学習リソースが適切でしょうか？",
    "async_execution": false
  }'
```

### パフォーマンステスト
```python
# パフォーマンス測定スクリプト
import time
import requests

def measure_memory_performance():
    start_time = time.time()
    
    # グラフメモリ使用
    response = requests.post("http://localhost:8000/tasks", json={
        "crew_name": "main_crew",
        "task": "複雑な知識検索タスク",
        "async_execution": False
    })
    
    end_time = time.time()
    return end_time - start_time, response.json()

# 測定実行
graph_time, graph_result = measure_memory_performance()
print(f"グラフメモリ使用時間: {graph_time:.2f}秒")
```

## 成功指標

### 定量的指標
- **検索精度向上**: 関連情報の検索ヒット率 20%以上向上
- **応答品質**: エンティティ関係を活用した回答の一貫性向上
- **メモリ効率**: 長期記憶の効果的な活用（セッション間での知識継承）

### 定性的指標
- **知識の関連性**: エンティティ間の関係を活用した包括的な回答
- **学習能力**: 新しい情報と既存知識の効果的な統合
- **コンテキスト理解**: 複雑な関係性を理解した推論能力

## 注意事項

### セキュリティとプライバシー
- Mem0 APIキーの適切な管理
- エンティティ情報の機密性保護
- グラフデータの暗号化（必要に応じて）

### パフォーマンス考慮事項
- 大規模グラフでの検索最適化
- メモリ使用量の監視
- API呼び出し頻度の制御

### 運用上の注意
- グラフメモリの定期的なクリーンアップ
- エンティティの重複管理
- 関係の品質管理（誤った関係の修正）

---

**作成日**: 2025-08-05  
**ステータス**: Ready for Implementation  
**前提条件**: タスク1完了  
**次の依存タスク**: タスク3（Evolution System改善）
**推定実装期間**: 3-4時間