# タスク7: ガードレール機能実装

## 📋 基本情報

**目標**: CrewAIのガードレール機能を正しく実装し、品質保証を実現  
**優先度**: 中  
**予想作業時間**: 4-5時間  
**担当者**: バックエンド開発者  
**前提条件**: Python開発経験、CrewAI理解

## 🔍 現状分析

### 現在の問題点
- **ガードレール未動作**: CrewAIのガードレール機能が機能していない
- **品質検証不足**: ハルシネーションや不適切な出力の検出ができない
- **検証基準の欠如**: 明確な品質基準が定義されていない

### 期待される改善効果
- **出力品質向上**: ハルシネーション防止
- **安全性向上**: 不適切な文言の検出と修正
- **信頼性向上**: ユーザー入力に即した回答の保証

### 検証対象
- ハルシネーション（事実と異なる内容）
- 不適切な文言（攻撃的、差別的な表現）
- 関連性（ユーザー入力との整合性）

## 🛠️ 実装手順

### Step 1: 現在のガードレール設定の確認

#### 1.1 既存実装の調査
```python
# guardrail_manager.pyの確認
import logging
from typing import Tuple, Any
from crewai import TaskOutput

logger = logging.getLogger(__name__)

class GuardrailManager:
    """現在のガードレール実装を確認"""
    def __init__(self):
        self.guardrails = []
    
    def validate_output(self, output: TaskOutput) -> Tuple[bool, Any]:
        # 現在の実装状況を確認
        pass
```

#### 1.2 CrewAI標準ガードレール機能の確認
```python
from crewai.guardrails import (
    LLMGuardrail,
    HallucinationGuardrail,
    ContentGuardrail
)

# CrewAIの標準ガードレール機能を調査
```

### Step 2: ガードレール実装の設計

#### 2.1 カスタムガードレールクラス
```python
# guardrails/hallucination_guardrail.py
from typing import Tuple, Any, Dict
from crewai import TaskOutput
import logging

logger = logging.getLogger(__name__)

class HallucinationDetector:
    """ハルシネーション検出ガードレール"""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.fact_checker = self._initialize_fact_checker()
    
    def validate(self, output: TaskOutput) -> Tuple[bool, Any]:
        """
        出力内容のファクトチェック
        
        Returns:
            (is_valid, error_message or output)
        """
        try:
            # コンテキストとの整合性チェック
            context_consistency = self._check_context_consistency(output)
            
            # 既知の事実との照合
            fact_accuracy = self._check_facts(output)
            
            # 総合スコアの計算
            confidence_score = (context_consistency + fact_accuracy) / 2
            
            if confidence_score >= self.threshold:
                logger.info(f"ハルシネーションチェック合格: スコア {confidence_score:.2f}")
                return True, output
            else:
                logger.warning(f"ハルシネーション検出: スコア {confidence_score:.2f}")
                return False, f"信頼性スコアが低い: {confidence_score:.2f}"
                
        except Exception as e:
            logger.error(f"ハルシネーションチェックエラー: {str(e)}")
            return False, f"検証エラー: {str(e)}"
    
    def _check_context_consistency(self, output: TaskOutput) -> float:
        """コンテキストとの整合性をチェック"""
        # タスクの入力と出力の関連性を評価
        if hasattr(output, 'task') and hasattr(output.task, 'description'):
            # 簡単な実装例：キーワードマッチング
            task_keywords = set(output.task.description.lower().split())
            output_keywords = set(str(output.raw).lower().split())
            
            overlap = len(task_keywords & output_keywords)
            score = overlap / max(len(task_keywords), 1)
            return min(score * 2, 1.0)  # スコアを0-1に正規化
        return 0.5
    
    def _check_facts(self, output: TaskOutput) -> float:
        """事実の正確性をチェック"""
        # ナレッジベースとの照合
        # 実装例：知識ファイルとの整合性チェック
        return 0.8  # 仮の値
    
    def _initialize_fact_checker(self):
        """ファクトチェッカーの初期化"""
        # 知識ベースやAPIとの連携設定
        pass
```

#### 2.2 不適切コンテンツ検出ガードレール
```python
# guardrails/content_filter_guardrail.py
import re
from typing import Tuple, Any, List

class ContentFilterGuardrail:
    """不適切なコンテンツを検出・フィルタリング"""
    
    def __init__(self):
        self.prohibited_patterns = self._load_prohibited_patterns()
        self.sensitive_topics = self._load_sensitive_topics()
    
    def validate(self, output: TaskOutput) -> Tuple[bool, Any]:
        """
        不適切な内容をチェック
        """
        content = str(output.raw).lower()
        
        # 禁止パターンのチェック
        for pattern in self.prohibited_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"不適切なコンテンツ検出: {pattern}")
                return False, "不適切な内容が含まれています"
        
        # センシティブトピックの警告
        warnings = []
        for topic in self.sensitive_topics:
            if topic in content:
                warnings.append(topic)
        
        if warnings:
            logger.info(f"センシティブトピック検出（許可）: {warnings}")
            # 警告はするが、ブロックはしない
            output.metadata = output.metadata or {}
            output.metadata['warnings'] = warnings
        
        return True, output
    
    def _load_prohibited_patterns(self) -> List[str]:
        """禁止パターンのロード"""
        return [
            r'\b(攻撃的|差別的|侮辱的)\b',
            # 実際の禁止ワードリスト
        ]
    
    def _load_sensitive_topics(self) -> List[str]:
        """センシティブトピックのロード"""
        return [
            '医療', '法律', '金融アドバイス'
        ]
```

#### 2.3 関連性チェックガードレール
```python
# guardrails/relevance_guardrail.py
from typing import Tuple, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class RelevanceGuardrail:
    """ユーザー入力との関連性をチェック"""
    
    def __init__(self, min_relevance: float = 0.5):
        self.min_relevance = min_relevance
        self.embedder = self._initialize_embedder()
    
    def validate(self, output: TaskOutput) -> Tuple[bool, Any]:
        """
        タスクと出力の関連性を検証
        """
        if not hasattr(output, 'task'):
            return True, output  # タスク情報がない場合はスキップ
        
        try:
            # タスクと出力のエンベディング取得
            task_embedding = self._get_embedding(output.task.description)
            output_embedding = self._get_embedding(str(output.raw))
            
            # コサイン類似度計算
            relevance_score = cosine_similarity(
                [task_embedding], 
                [output_embedding]
            )[0][0]
            
            if relevance_score >= self.min_relevance:
                logger.info(f"関連性チェック合格: スコア {relevance_score:.2f}")
                return True, output
            else:
                logger.warning(f"関連性が低い: スコア {relevance_score:.2f}")
                return False, f"タスクとの関連性が低い: {relevance_score:.2f}"
                
        except Exception as e:
            logger.error(f"関連性チェックエラー: {str(e)}")
            # エラーの場合は通過させる（厳しすぎないように）
            return True, output
    
    def _initialize_embedder(self):
        """エンベディングモデルの初期化"""
        # OpenAI Embeddingsまたは他のモデル
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings()
    
    def _get_embedding(self, text: str):
        """テキストのエンベディング取得"""
        return self.embedder.embed_query(text)
```

### Step 3: ガードレールマネージャーの統合

#### 3.1 GuardrailManagerの更新
```python
# core/guardrail_manager.py
from typing import List, Tuple, Any, Dict
from crewai import TaskOutput
import logging

logger = logging.getLogger(__name__)

class GuardrailManager:
    """統合ガードレールマネージャー"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.guardrails = []
        self._initialize_guardrails()
    
    def _initialize_guardrails(self):
        """ガードレールの初期化"""
        from guardrails.hallucination_guardrail import HallucinationDetector
        from guardrails.content_filter_guardrail import ContentFilterGuardrail
        from guardrails.relevance_guardrail import RelevanceGuardrail
        
        # 設定に基づいてガードレールを有効化
        if self.config.get('hallucination_check', True):
            self.guardrails.append(HallucinationDetector())
        
        if self.config.get('content_filter', True):
            self.guardrails.append(ContentFilterGuardrail())
        
        if self.config.get('relevance_check', True):
            self.guardrails.append(RelevanceGuardrail())
        
        logger.info(f"初期化されたガードレール: {len(self.guardrails)}個")
    
    def validate_output(self, output: TaskOutput) -> Tuple[bool, Any]:
        """
        すべてのガードレールで出力を検証
        """
        for guardrail in self.guardrails:
            try:
                is_valid, result = guardrail.validate(output)
                if not is_valid:
                    logger.warning(f"ガードレール {guardrail.__class__.__name__} が失敗: {result}")
                    return False, result
            except Exception as e:
                logger.error(f"ガードレール {guardrail.__class__.__name__} でエラー: {str(e)}")
                # エラーがあってもスキップ（fail-open）
                continue
        
        logger.info("すべてのガードレールチェックに合格")
        return True, output
    
    def add_guardrail(self, guardrail):
        """カスタムガードレールの追加"""
        self.guardrails.append(guardrail)
        logger.info(f"ガードレール追加: {guardrail.__class__.__name__}")
    
    def remove_guardrail(self, guardrail_name: str):
        """ガードレールの削除"""
        self.guardrails = [
            g for g in self.guardrails 
            if g.__class__.__name__ != guardrail_name
        ]
```

### Step 4: CrewAIタスクへの統合

#### 4.1 タスク設定での統合
```yaml
# config/tasks/research_task.yaml
research_task:
  description: "調査タスク"
  expected_output: "詳細な調査レポート"
  guardrails:
    - hallucination_check: true
    - content_filter: true
    - relevance_check: true
  max_retries: 3  # ガードレール失敗時のリトライ回数
```

#### 4.2 Crew実行時の統合
```python
# crews/crew_factory.py
def create_crew(self, crew_name: str):
    # ...既存のコード...
    
    # ガードレールマネージャーの初期化
    guardrail_manager = GuardrailManager(
        config=crew_config.get('guardrails', {})
    )
    
    # タスクにガードレール設定
    for task in tasks:
        task.guardrail = lambda output: guardrail_manager.validate_output(output)
    
    return crew
```

## ✅ 実装チェックリスト

### 必須項目
- [ ] HallucinationDetectorが実装されている
- [ ] ContentFilterGuardrailが実装されている
- [ ] RelevanceGuardrailが実装されている
- [ ] GuardrailManagerが統合されている
- [ ] タスク実行時にガードレールが動作する

### 推奨項目
- [ ] ガードレール設定がYAMLで管理できる
- [ ] ログ出力が適切
- [ ] エラーハンドリングが実装されている
- [ ] パフォーマンスへの影響が最小限

## 📊 成功指標

### 定量的指標
- **ハルシネーション検出率**: 80%以上
- **不適切コンテンツブロック率**: 95%以上
- **関連性スコア平均**: 0.7以上
- **処理時間増加**: 20%以内

### 定性的指標
- **出力品質の向上**: ユーザーフィードバックで確認
- **信頼性の向上**: エラー報告の減少
- **安全性の確保**: 不適切な出力ゼロ

## 🔒 注意事項

### 重要な制約
- CrewAIの標準機能を破壊しない
- パフォーマンスへの影響を最小限に
- fail-openポリシー（エラー時は通過）

### リスクと対策
| リスク | 影響度 | 対策 |
|--------|--------|------|
| 過度なブロック | 高 | 閾値の調整可能性 |
| パフォーマンス低下 | 中 | キャッシュ機能実装 |
| 誤検出 | 中 | ログとモニタリング |

## 🔄 トラブルシューティング

### 問題1: ガードレールが動作しない
**症状**: 明らかに問題のある出力が通過する  
**原因**: ガードレール設定が無効  
**対処法**:
```python
# デバッグモードで確認
logger.setLevel(logging.DEBUG)
# ガードレールの状態確認
print(f"Active guardrails: {guardrail_manager.guardrails}")
```

### 問題2: 過度なブロック
**症状**: 正常な出力もブロックされる  
**原因**: 閾値が厳しすぎる  
**対処法**: 設定ファイルで閾値調整

## 📚 関連リソース

### 内部リンク
- [ログ出力最適化タスク](./task_08_log_optimization.md)
- [知識グラフ統合タスク](./task_09_knowledge_graph_integration.md)

### 外部リソース
- [CrewAI Guardrails Documentation](https://docs.crewai.com/guardrails)
- [LLM Safety Best Practices](https://www.anthropic.com/safety)

---

**作成日**: 2025-08-02  
**最終更新**: 2025-08-02  
**作成者**: OKAMI Development Team  
**ステータス**: Ready for Implementation  
**次の依存タスク**: ログ出力最適化タスク