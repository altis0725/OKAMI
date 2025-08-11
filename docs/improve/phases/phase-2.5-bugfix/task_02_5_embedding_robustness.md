# タスク 2.5.3: エンベディング生成の堅牢化

## 概要
エンベディング生成エラーを防ぎ、空配列エラーによるシステムクラッシュを解決します。

## 問題の詳細

### エラー内容
- `Error during entities search: Expected Embedings to be non-empty list or numpy array, got [] in query.`

### 原因分析
- エンベディング生成が失敗し、空の配列が返されている
- OpenAI API キーの問題またはエンベディングモデルへのアクセス不可
- エンベディング生成前のテキスト前処理の問題

## 作業内容

### 1. 入力検証の強化
- **ファイル**: `core/embedding_manager.py` (新規作成)
- **作業項目**:
  - エンベディング生成前の入力検証
  - 空文字列やNullチェックの追加
  - テキストの前処理とクリーニング

### 2. フォールバックプロバイダーの実装
- **作業項目**:
  - HuggingFaceモデルへの自動切り替え
  - ローカルエンベディングモデルの統合
  - プロバイダー失敗時の代替手段

### 3. エラーハンドリングの改善
- **作業項目**:
  - 詳細なエラーログの実装
  - 段階的なフォールバック戦略
  - リトライメカニズムの実装

### 4. 実装例

```python
# core/embedding_manager.py の実装例
import logging
from typing import List, Optional, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbeddingManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.primary_provider = config.get('primary_provider', 'openai')
        self.fallback_provider = config.get('fallback_provider', 'huggingface')
        self.embedding_dimension = config.get('embedding_dimension', 1536)
        
        # HuggingFace fallback model
        self.fallback_model = None
        self._init_fallback_model()
    
    def _init_fallback_model(self):
        """フォールバックモデルの初期化"""
        try:
            model_name = self.config.get('fallback_model', 'sentence-transformers/all-MiniLM-L6-v2')
            self.fallback_model = SentenceTransformer(model_name)
            self.embedding_dimension = self.fallback_model.get_sentence_embedding_dimension()
            logger.info(f"Fallback embedding model initialized: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize fallback embedding model: {e}")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """テキストのエンベディングを生成（改善版）"""
        if not texts:
            logger.warning("Empty text list provided for embedding generation")
            return []
        
        # 空文字列をフィルタリング
        processed_texts = []
        original_indices = []
        
        for i, text in enumerate(texts):
            if text and text.strip():
                processed_texts.append(text.strip())
                original_indices.append(i)
        
        if not processed_texts:
            logger.warning("No valid texts after filtering empty strings")
            return self._generate_dummy_embeddings(len(texts))
        
        # プライマリプロバイダーで試行
        try:
            embeddings = self._generate_with_primary(processed_texts)
            if embeddings and all(len(emb) > 0 for emb in embeddings):
                return self._restore_original_order(embeddings, original_indices, len(texts))
        except Exception as e:
            logger.warning(f"Primary embedding generation failed: {e}")
        
        # フォールバックプロバイダーで試行
        try:
            embeddings = self._generate_with_fallback(processed_texts)
            return self._restore_original_order(embeddings, original_indices, len(texts))
        except Exception as e:
            logger.error(f"Fallback embedding generation failed: {e}")
            return self._generate_dummy_embeddings(len(texts))
    
    def _generate_with_primary(self, texts: List[str]) -> List[List[float]]:
        """プライマリプロバイダーでエンベディング生成"""
        if self.primary_provider == 'openai':
            return self._generate_openai_embeddings(texts)
        else:
            raise ValueError(f"Unsupported primary provider: {self.primary_provider}")
    
    def _generate_with_fallback(self, texts: List[str]) -> List[List[float]]:
        """フォールバックプロバイダーでエンベディング生成"""
        if not self.fallback_model:
            raise RuntimeError("Fallback model not available")
        
        embeddings = self.fallback_model.encode(texts)
        return [emb.tolist() for emb in embeddings]
    
    def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """OpenAI APIでエンベディング生成"""
        import openai
        
        api_key = self.config.get('openai_api_key')
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        client = openai.OpenAI(api_key=api_key)
        
        response = client.embeddings.create(
            model=self.config.get('openai_model', 'text-embedding-3-small'),
            input=texts
        )
        
        return [data.embedding for data in response.data]
    
    def _generate_dummy_embeddings(self, count: int) -> List[List[float]]:
        """ダミーエンベディングを生成"""
        logger.warning(f"Generating dummy embeddings for {count} texts")
        return [[0.0] * self.embedding_dimension for _ in range(count)]
    
    def _restore_original_order(self, embeddings: List[List[float]], 
                              original_indices: List[int], 
                              total_count: int) -> List[List[float]]:
        """元の順序でエンベディングを復元"""
        result = []
        emb_idx = 0
        
        for i in range(total_count):
            if i in original_indices:
                result.append(embeddings[emb_idx])
                emb_idx += 1
            else:
                result.append([0.0] * self.embedding_dimension)
        
        return result
```

## 成功条件
- [ ] エンベディング生成で空配列エラーが発生しない
- [ ] 空文字列入力が適切に処理される
- [ ] フォールバックメカニズムが動作する
- [ ] OpenAI APIエラー時にHuggingFaceが使用される
- [ ] 詳細なエラーログが出力される

## 所要時間
**予想作業時間**: 4-5時間

## 優先度
**高** - システム全体の安定性に影響

## 前提条件
- HuggingFace Transformersライブラリのインストール
- sentence-transformersライブラリの利用可能性
- 適切なエンベディングモデルのダウンロード

## 検証方法
1. 空文字列でのエンベディング生成テスト
2. OpenAI API無効時のフォールバックテスト
3. 大量テキストでの処理テスト
4. メモリ使用量の確認
5. 処理速度のベンチマーク

## 依存関係
```txt
sentence-transformers>=2.2.0
torch>=1.11.0
transformers>=4.20.0
```