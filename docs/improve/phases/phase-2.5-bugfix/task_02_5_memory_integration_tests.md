# タスク 2.5.4: メモリーシステム統合テスト

## 概要
修正後のメモリーシステムの動作確認と品質保証のための統合テスト実装。

## 目的
- 修正されたメモリーシステムの動作検証
- 回帰テストの自動化
- CI/CDパイプラインでの品質保証

## 作業内容

### 1. Mem0接続テスト
- **ファイル**: `tests/test_memory_integration.py` (新規作成)
- **テスト項目**:
  - 有効なAPIキーでの接続テスト
  - 無効なAPIキーでのフォールバックテスト
  - API呼び出しのタイムアウトテスト
  - リトライメカニズムのテスト

### 2. ChromaDB操作テスト
- **テスト項目**:
  - ベクトル追加操作のE2Eテスト
  - ベクトル検索操作のE2Eテスト
  - タイムアウト処理のテスト
  - 並行処理での安定性テスト

### 3. エンベディング生成テスト
- **ファイル**: `tests/test_embedding_manager.py` (新規作成)
- **テスト項目**:
  - 正常なエンベディング生成
  - 空文字列処理のテスト
  - プロバイダーフォールバックのテスト
  - エラーハンドリングのテスト

### 4. 統合テスト実装

```python
# tests/test_memory_integration.py
import pytest
import asyncio
from unittest.mock import Mock, patch
from core.memory_manager import MemoryManager
from core.embedding_manager import EmbeddingManager

class TestMemoryIntegration:
    
    @pytest.fixture
    async def memory_manager(self):
        """テスト用メモリーマネージャーの準備"""
        config = {
            'use_mem0': True,
            'chroma_db_path': './test_storage/chroma_db',
            'embedding_provider': 'ollama'
        }
        manager = MemoryManager(config)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_mem0_connection_success(self, memory_manager):
        """Mem0正常接続のテスト"""
        with patch.dict('os.environ', {'MEM0_API_KEY': 'valid_key'}):
            result = await memory_manager.test_mem0_connection()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_mem0_connection_fallback(self, memory_manager):
        """Mem0接続失敗時のフォールバックテスト"""
        with patch.dict('os.environ', {'MEM0_API_KEY': 'invalid_key'}):
            # 初期化時にフォールバックが動作することを確認
            assert memory_manager.use_mem0 is False
            assert memory_manager.external_memory is None
    
    @pytest.mark.asyncio
    async def test_vector_search_with_timeout(self, memory_manager):
        """ベクトル検索のタイムアウトテスト"""
        query = "test query"
        
        # タイムアウトが発生する条件をシミュレート
        with patch('core.vector_store.VectorStore.search') as mock_search:
            mock_search.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(asyncio.TimeoutError):
                await memory_manager.search_memories(query, timeout=1)
    
    @pytest.mark.asyncio
    async def test_memory_save_and_retrieve(self, memory_manager):
        """メモリー保存・検索のE2Eテスト"""
        test_content = "This is a test memory"
        test_metadata = {"type": "test", "timestamp": "2024-01-01"}
        
        # 保存
        memory_id = await memory_manager.save_memory(
            content=test_content, 
            metadata=test_metadata
        )
        assert memory_id is not None
        
        # 検索
        results = await memory_manager.search_memories("test memory", limit=5)
        assert len(results) > 0
        assert any(test_content in result['content'] for result in results)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, memory_manager):
        """並行処理での安定性テスト"""
        tasks = []
        
        # 複数のメモリー保存を並行実行
        for i in range(10):
            task = memory_manager.save_memory(
                content=f"Concurrent test memory {i}",
                metadata={"index": i}
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外が発生していないことを確認
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0
```

```python
# tests/test_embedding_manager.py
import pytest
from unittest.mock import Mock, patch
from core.embedding_manager import EmbeddingManager

class TestEmbeddingManager:
    
    @pytest.fixture
    def embedding_manager(self):
        """テスト用エンベディングマネージャー"""
        config = {
            'primary_provider': 'openai',
            'fallback_provider': 'huggingface',
            'embedding_dimension': 384
        }
        return EmbeddingManager(config)
    
    def test_normal_embedding_generation(self, embedding_manager):
        """正常なエンベディング生成テスト"""
        texts = ["Hello world", "Test embedding"]
        
        with patch.object(embedding_manager, '_generate_with_primary') as mock_primary:
            mock_primary.return_value = [[0.1, 0.2], [0.3, 0.4]]
            
            embeddings = embedding_manager.generate_embeddings(texts)
            
            assert len(embeddings) == 2
            assert all(len(emb) > 0 for emb in embeddings)
    
    def test_empty_string_handling(self, embedding_manager):
        """空文字列処理のテスト"""
        texts = ["", "  ", "valid text", None]
        
        embeddings = embedding_manager.generate_embeddings(texts)
        
        assert len(embeddings) == 4
        # 無効な入力にはダミーエンベディングが返される
        assert all(len(emb) == embedding_manager.embedding_dimension for emb in embeddings)
    
    def test_primary_provider_fallback(self, embedding_manager):
        """プライマリプロバイダー失敗時のフォールバックテスト"""
        texts = ["test"]
        
        with patch.object(embedding_manager, '_generate_with_primary') as mock_primary:
            mock_primary.side_effect = Exception("OpenAI API error")
            
            with patch.object(embedding_manager, '_generate_with_fallback') as mock_fallback:
                mock_fallback.return_value = [[0.1, 0.2, 0.3]]
                
                embeddings = embedding_manager.generate_embeddings(texts)
                
                assert len(embeddings) == 1
                mock_primary.assert_called_once()
                mock_fallback.assert_called_once()
    
    def test_complete_failure_dummy_generation(self, embedding_manager):
        """完全失敗時のダミーエンベディング生成テスト"""
        texts = ["test"]
        
        with patch.object(embedding_manager, '_generate_with_primary') as mock_primary:
            mock_primary.side_effect = Exception("Primary failed")
            
            with patch.object(embedding_manager, '_generate_with_fallback') as mock_fallback:
                mock_fallback.side_effect = Exception("Fallback failed")
                
                embeddings = embedding_manager.generate_embeddings(texts)
                
                assert len(embeddings) == 1
                assert len(embeddings[0]) == embedding_manager.embedding_dimension
                assert all(val == 0.0 for val in embeddings[0])
```

### 5. CI/CD統合

```yaml
# .github/workflows/memory_tests.yml (新規作成)
name: Memory System Tests

on:
  push:
    paths:
      - 'core/memory_manager.py'
      - 'core/embedding_manager.py'
      - 'core/vector_store.py'
      - 'tests/test_memory_*.py'
  pull_request:
    paths:
      - 'core/memory_manager.py'
      - 'core/embedding_manager.py' 
      - 'core/vector_store.py'
      - 'tests/test_memory_*.py'

jobs:
  memory-tests:
    runs-on: ubuntu-latest
    
    services:
      chroma:
        image: chromadb/chroma:latest
        ports:
          - 8000:8000
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install pytest pytest-asyncio pytest-cov
        pip install -r requirements.txt
    
    - name: Run memory integration tests
      env:
        CHROMA_DB_PATH: ./test_storage/chroma_db
      run: |
        pytest tests/test_memory_integration.py -v --cov=core
    
    - name: Run embedding manager tests
      run: |
        pytest tests/test_embedding_manager.py -v --cov=core/embedding_manager.py
```

## 成功条件
- [ ] すべてのテストが成功する
- [ ] テストカバレッジが80%以上
- [ ] CI/CDパイプラインでテストが自動実行される
- [ ] フォールバック機能のテストが網羅的
- [ ] エラーケースのテストが充実している

## 所要時間
**予想作業時間**: 5-6時間

## 優先度
**中** - 品質保証のため

## 前提条件
- pytest関連パッケージのインストール
- テスト用ChromaDBの準備
- モックライブラリの準備

## 検証方法
1. ローカルでのテスト実行
2. CI/CD環境でのテスト実行
3. カバレッジレポートの確認
4. エラーケースの網羅性確認

## テスト実行コマンド
```bash
# 全テスト実行
python -m pytest tests/test_memory_*.py -v

# カバレッジ付きテスト
python -m pytest tests/test_memory_*.py --cov=core --cov-report=html

# 特定のテストクラス実行
python -m pytest tests/test_memory_integration.py::TestMemoryIntegration -v
```