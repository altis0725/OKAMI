# タスク3: Evolution System改善提案機能向上

## タスク概要

**目標**: 自動生成される改善提案をより具体的で実装可能なものにする  
**優先度**: 中  
**予想作業時間**: 3-4時間  
**担当者**: AI Assistant  
**前提条件**: タスク1, 2完了、Python開発経験

## 現状分析

### 現在のEvolution Systemの構成
```
evolution/
├── improvement_parser.py - 改善分析結果の解析
├── improvement_applier.py - 改善点の自動適用
├── backups/ - 変更前の自動バックアップ
└── __init__.py
```

### 現在の問題点
1. **改善提案の抽象性**: 具体的な実装手順が不明確
2. **成功率の低さ**: 提案が実際に適用できない場合が多い
3. **フィードバックループ不足**: 改善提案の効果測定ができていない
4. **テンプレート化不足**: 改善提案の品質が不安定

### Evolution Systemの動作フロー分析
```
1. タスク実行完了
2. Evolution Crew起動
3. 実行結果分析
4. improvement_parser.pyで改善点抽出
5. improvement_applier.pyで変更適用
6. バックアップ作成
```

## 実装手順

### Step 1: 現状システムの詳細分析

#### 1.1 improvement_parser.pyの分析
```python
# 調査すべき項目
- 現在の解析ロジック
- 改善提案の生成方法
- 出力フォーマット
- エラーハンドリング
```

#### 1.2 improvement_applier.pyの分析  
```python
# 調査すべき項目
- 適用可能な改善パターン
- ファイル変更の方法
- 失敗時の処理
- バックアップ機能
```

#### 1.3 現在の改善提案例の収集
```bash
# 最近の改善履歴確認
cat storage/evolution/evolution_history.json | jq '.[] | select(.timestamp > "2025-08-01")'

# 実際に適用された改善の分析
ls evolution/backups/ | head -10
```

### Step 2: 改善提案テンプレートシステムの構築

#### 2.1 テンプレートディレクトリ構造
```
evolution/
├── templates/
│   ├── README.md - テンプレート使用ガイド
│   ├── knowledge_improvement.yaml - ナレッジファイル改善
│   ├── agent_config_improvement.yaml - エージェント設定改善
│   ├── task_config_improvement.yaml - タスク設定改善
│   ├── system_config_improvement.yaml - システム設定改善
│   └── general_improvement.yaml - 一般的な改善
├── metrics.py - 改善効果測定
├── template_engine.py - テンプレート処理エンジン
└── [既存ファイル]
```

#### 2.2 改善提案テンプレート例

**knowledge_improvement.yaml**
```yaml
# ナレッジファイル改善テンプレート
template_type: knowledge_improvement
version: 1.0

structure:
  analysis:
    - problem_identification: "具体的な問題の特定"
    - root_cause: "根本原因の分析"
    - impact_assessment: "影響範囲の評価"
  
  solution:
    - approach: "解決方法の概要"
    - implementation_steps: "実装手順（5ステップ以内）"
    - expected_outcome: "期待される結果"
    - validation_method: "検証方法"
  
  specifics:
    - target_files: ["対象ファイルのリスト"]
    - changes_required: "必要な変更の詳細"
    - dependencies: "依存関係"
    - risks: "潜在的リスク"

quality_criteria:
  - specificity: "具体性（1-10スコア）"
  - implementability: "実装可能性（1-10スコア）"  
  - measurability: "測定可能性（1-10スコア）"
  - relevance: "関連性（1-10スコア）"

validation:
  pre_checks:
    - "ファイル存在確認"
    - "バックアップ作成"
    - "構文チェック"
  
  post_checks:
    - "機能テスト"
    - "品質測定"
    - "回帰テスト"

example:
  problem: "general.mdの構造が不明確で検索効率が低い"
  solution: "目次とセクション分けによる構造化"
  steps:
    1. "現在の内容をバックアップ"
    2. "目次構造を設計"
    3. "セクション分けして内容再編成"
    4. "クロスリファレンス追加"
    5. "検索テストで効果確認"
  files: ["knowledge/general.md"]
  validation: "ナレッジ検索ヒット率の改善測定"
```

**agent_config_improvement.yaml**
```yaml
# エージェント設定改善テンプレート  
template_type: agent_config_improvement
version: 1.0

structure:
  analysis:
    - performance_issue: "パフォーマンス問題の特定"
    - config_gap: "設定の不備"
    - optimization_opportunity: "最適化の機会"
  
  solution:
    - config_changes: "設定変更内容"
    - parameter_tuning: "パラメータ調整"
    - new_capabilities: "新機能追加"
  
  implementation:
    - target_agents: ["対象エージェントリスト"]
    - config_files: ["設定ファイルパス"]
    - parameter_changes: "パラメータ変更詳細"
    - testing_approach: "テスト方法"

quality_criteria:
  - performance_improvement: "性能向上見込み"
  - backward_compatibility: "後方互換性"
  - resource_efficiency: "リソース効率"

example:
  problem: "Research Agentの情報収集が浅い"
  solution: "max_iterを15から25に増加、新しいリサーチツール追加"
  changes:
    - file: "config/agents/research_agent.yaml"
    - parameter: "max_iter: 25"
    - tools: ["web_search", "document_analysis"]
  validation: "リサーチ品質の主観評価テスト"
```

#### 2.3 テンプレートエンジンの実装

**evolution/template_engine.py**
```python
import yaml
from typing import Dict, List, Any
from pathlib import Path

class ImprovementTemplateEngine:
    def __init__(self, templates_dir: str = "evolution/templates"):
        self.templates_dir = Path(templates_dir)
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Any]:
        """テンプレートファイルを読み込み"""
        templates = {}
        for template_file in self.templates_dir.glob("*.yaml"):
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
                templates[template_data['template_type']] = template_data
        return templates
    
    def generate_improvement_proposal(
        self, 
        template_type: str, 
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """改善提案を生成"""
        if template_type not in self.templates:
            raise ValueError(f"Unknown template type: {template_type}")
        
        template = self.templates[template_type]
        proposal = self._fill_template(template, analysis_data)
        proposal['quality_score'] = self._calculate_quality_score(proposal)
        
        return proposal
    
    def _fill_template(self, template: Dict, data: Dict) -> Dict:
        """テンプレートにデータを適用"""
        # テンプレート適用ロジック
        pass
    
    def _calculate_quality_score(self, proposal: Dict) -> float:
        """品質スコアを計算"""
        criteria = proposal.get('quality_criteria', {})
        # スコア計算ロジック
        pass
    
    def validate_proposal(self, proposal: Dict) -> Dict[str, bool]:
        """提案の検証"""
        validation_results = {}
        
        # 事前チェック
        pre_checks = proposal.get('validation', {}).get('pre_checks', [])
        for check in pre_checks:
            validation_results[f"pre_{check}"] = self._run_check(check, proposal)
        
        return validation_results
    
    def _run_check(self, check: str, proposal: Dict) -> bool:
        """個別チェックの実行"""
        # チェックロジック
        pass
```

### Step 3: 改善効果測定システムの実装

#### 3.1 メトリクス定義

**evolution/metrics.py**
```python
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
from pathlib import Path

class ImprovementMetrics:
    def __init__(self, storage_path: str = "storage/evolution"):
        self.storage_path = Path(storage_path)
        self.metrics_file = self.storage_path / "improvement_metrics.json"
    
    def record_improvement_attempt(
        self, 
        improvement_id: str,
        proposal: Dict[str, Any],
        success: bool,
        execution_time: float,
        error_msg: str = None
    ):
        """改善試行の記録"""
        metric = {
            "improvement_id": improvement_id,
            "timestamp": datetime.now().isoformat(),
            "template_type": proposal.get("template_type"),
            "quality_score": proposal.get("quality_score", 0),
            "success": success,
            "execution_time": execution_time,
            "error_message": error_msg,
            "target_files": proposal.get("specifics", {}).get("target_files", [])
        }
        
        self._append_metric(metric)
    
    def calculate_success_rate(self, period_days: int = 30) -> Dict[str, float]:
        """成功率の計算"""
        cutoff_date = datetime.now() - timedelta(days=period_days)
        recent_metrics = self._get_recent_metrics(cutoff_date)
        
        total = len(recent_metrics)
        if total == 0:
            return {"overall": 0.0}
        
        successful = sum(1 for m in recent_metrics if m["success"])
        
        # テンプレートタイプ別成功率
        by_type = {}
        for template_type in set(m.get("template_type") for m in recent_metrics):
            type_metrics = [m for m in recent_metrics if m.get("template_type") == template_type]
            type_successful = sum(1 for m in type_metrics if m["success"])
            by_type[template_type] = type_successful / len(type_metrics)
        
        return {
            "overall": successful / total,
            "by_template_type": by_type,
            "total_attempts": total
        }
    
    def get_quality_trends(self, period_days: int = 30) -> Dict[str, Any]:
        """品質トレンドの分析"""
        cutoff_date = datetime.now() - timedelta(days=period_days)
        recent_metrics = self._get_recent_metrics(cutoff_date)
        
        if not recent_metrics:
            return {"trend": "no_data"}
        
        # 時系列での品質スコア変化
        quality_scores = [m.get("quality_score", 0) for m in recent_metrics]
        
        return {
            "average_quality": sum(quality_scores) / len(quality_scores),
            "quality_trend": self._calculate_trend(quality_scores),
            "score_distribution": self._get_score_distribution(quality_scores)
        }
    
    def identify_improvement_patterns(self) -> Dict[str, Any]:
        """改善パターンの特定"""
        all_metrics = self._load_all_metrics()
        
        # 成功パターンの分析
        successful_improvements = [m for m in all_metrics if m.get("success")]
        
        patterns = {
            "most_successful_templates": self._get_template_rankings(successful_improvements),
            "optimal_quality_range": self._find_optimal_quality_range(all_metrics),
            "common_failure_reasons": self._analyze_failures(all_metrics)
        }
        
        return patterns
    
    def _append_metric(self, metric: Dict[str, Any]):
        """メトリクスファイルに追記"""
        metrics = self._load_all_metrics()
        metrics.append(metric)
        
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    def _load_all_metrics(self) -> List[Dict[str, Any]]:
        """全メトリクスの読み込み"""
        if not self.metrics_file.exists():
            return []
        
        with open(self.metrics_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_recent_metrics(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """指定日以降のメトリクス取得"""
        all_metrics = self._load_all_metrics()
        return [
            m for m in all_metrics 
            if datetime.fromisoformat(m["timestamp"]) >= cutoff_date
        ]
```

### Step 4: 改善されたimprovement_parser.pyの実装

#### 4.1 新しいparser.pyの設計
```python
from evolution.template_engine import ImprovementTemplateEngine
from evolution.metrics import ImprovementMetrics
from typing import Dict, List, Any
import logging

class EnhancedImprovementParser:
    def __init__(self):
        self.template_engine = ImprovementTemplateEngine()
        self.metrics = ImprovementMetrics()
        self.logger = logging.getLogger(__name__)
    
    def parse_and_generate_improvements(
        self, 
        analysis_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """分析結果から改善提案を生成"""
        
        # 1. 分析結果の分類
        improvement_categories = self._categorize_analysis(analysis_result)
        
        # 2. 各カテゴリに対して適切なテンプレートを選択
        proposals = []
        for category, data in improvement_categories.items():
            template_type = self._select_template_type(category, data)
            
            try:
                proposal = self.template_engine.generate_improvement_proposal(
                    template_type, data
                )
                
                # 3. 品質チェック
                if self._meets_quality_threshold(proposal):
                    proposals.append(proposal)
                else:
                    self.logger.warning(f"Proposal for {category} did not meet quality threshold")
                    
            except Exception as e:
                self.logger.error(f"Failed to generate proposal for {category}: {str(e)}")
        
        # 4. 提案の優先順位付け
        prioritized_proposals = self._prioritize_proposals(proposals)
        
        return prioritized_proposals
    
    def _categorize_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Dict]:
        """分析結果をカテゴリ分類"""
        categories = {}
        
        # ナレッジ関連の問題
        if self._has_knowledge_issues(analysis):
            categories["knowledge"] = self._extract_knowledge_issues(analysis)
        
        # エージェント設定の問題  
        if self._has_agent_config_issues(analysis):
            categories["agent_config"] = self._extract_agent_issues(analysis)
        
        # タスク設定の問題
        if self._has_task_issues(analysis):
            categories["task_config"] = self._extract_task_issues(analysis)
        
        # システム設定の問題
        if self._has_system_issues(analysis):
            categories["system_config"] = self._extract_system_issues(analysis)
        
        return categories
    
    def _select_template_type(self, category: str, data: Dict) -> str:
        """カテゴリに基づいてテンプレートタイプを選択"""
        template_mapping = {
            "knowledge": "knowledge_improvement",
            "agent_config": "agent_config_improvement", 
            "task_config": "task_config_improvement",
            "system_config": "system_config_improvement"
        }
        
        return template_mapping.get(category, "general_improvement")
    
    def _meets_quality_threshold(self, proposal: Dict[str, Any]) -> bool:
        """品質閾値をチェック"""
        quality_score = proposal.get("quality_score", 0)
        
        # 過去の成功パターンに基づく動的閾値
        patterns = self.metrics.identify_improvement_patterns()
        optimal_range = patterns.get("optimal_quality_range", {})
        min_threshold = optimal_range.get("min", 6.0)
        
        return quality_score >= min_threshold
    
    def _prioritize_proposals(self, proposals: List[Dict]) -> List[Dict]:
        """提案の優先順位付け"""
        def priority_score(proposal):
            # 品質スコア、実装可能性、影響度を考慮
            quality = proposal.get("quality_score", 0)
            implementability = proposal.get("quality_criteria", {}).get("implementability", 0)
            impact = self._estimate_impact(proposal)
            
            return quality * 0.4 + implementability * 0.3 + impact * 0.3
        
        return sorted(proposals, key=priority_score, reverse=True)
    
    def _estimate_impact(self, proposal: Dict[str, Any]) -> float:
        """改善提案の影響度を推定"""
        # 対象ファイル数、変更範囲、期待効果に基づく推定
        target_files = len(proposal.get("specifics", {}).get("target_files", []))
        expected_outcome = proposal.get("solution", {}).get("expected_outcome", "")
        
        # 簡単な影響度算出ロジック
        impact_score = min(target_files * 2, 10)  # ファイル数ベース
        
        # 期待効果のキーワード分析
        high_impact_keywords = ["efficiency", "accuracy", "performance", "quality"]
        keyword_score = sum(2 for keyword in high_impact_keywords if keyword in expected_outcome.lower())
        
        return min(impact_score + keyword_score, 10) / 10
```

### Step 5: フィードバックループの実装

#### 5.1 改善適用後の効果測定
```python
class ImprovementEffectivenessTracker:
    def __init__(self):
        self.metrics = ImprovementMetrics()
    
    def track_improvement_effect(
        self, 
        improvement_id: str, 
        baseline_metrics: Dict[str, Any],
        period_days: int = 7
    ):
        """改善効果の追跡"""
        
        # 一定期間後の効果測定
        def measure_after_period():
            current_metrics = self._collect_current_metrics()
            effect = self._calculate_improvement_effect(
                baseline_metrics, 
                current_metrics
            )
            
            self.metrics.record_improvement_effect(
                improvement_id, 
                effect
            )
        
        # 非同期で期間後に測定実行
        # (実際の実装では適切なスケジューリングを使用)
        return measure_after_period
    
    def _collect_current_metrics(self) -> Dict[str, Any]:
        """現在のシステムメトリクスを収集"""
        # タスク成功率、実行時間、品質スコアなど
        pass
    
    def _calculate_improvement_effect(
        self, 
        baseline: Dict[str, Any], 
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """改善効果の計算"""
        # ベースラインとの比較
        pass
```

## 実装チェックリスト

### Phase 1: 分析と設計
- [ ] 現在のEvolution Systemコード分析完了
- [ ] 改善提案テンプレート設計完了
- [ ] メトリクス定義完了

### Phase 2: テンプレートシステム
- [ ] evolution/templates/ディレクトリ作成
- [ ] 各種テンプレートYAMLファイル作成
- [ ] template_engine.py実装
- [ ] テンプレート動作テスト

### Phase 3: メトリクスシステム
- [ ] metrics.py実装
- [ ] 改善効果測定機能実装
- [ ] メトリクス収集テスト

### Phase 4: パーサー改善
- [ ] EnhancedImprovementParser実装
- [ ] 既存improvement_parser.pyとの統合
- [ ] 品質チェック機能テスト

### Phase 5: フィードバックループ
- [ ] 効果追跡機能実装
- [ ] 自動改善サイクル構築
- [ ] 長期的効果測定

## 検証方法

### 単体テスト
```python
# テンプレートエンジンテスト
def test_template_engine():
    engine = ImprovementTemplateEngine()
    proposal = engine.generate_improvement_proposal(
        "knowledge_improvement",
        {"problem": "test problem", "analysis": "test analysis"}
    )
    assert proposal["quality_score"] > 0

# メトリクステスト  
def test_metrics_recording():
    metrics = ImprovementMetrics()
    metrics.record_improvement_attempt(
        "test_improvement",
        {"template_type": "knowledge_improvement", "quality_score": 7.5},
        True,
        2.5
    )
    success_rate = metrics.calculate_success_rate(1)
    assert success_rate["overall"] >= 0
```

### 統合テスト
```bash
# 改善提案生成から適用までの全フローテスト
python -m pytest tests/test_evolution_system.py -v

# 実際のタスク実行での改善効果測定
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "crew_name": "evolution_crew",
    "task": "最近のタスク実行結果を分析して、具体的で実装可能な改善提案を3つ生成してください",
    "async_execution": false
  }'
```

## 成功指標

### 定量的指標
- 改善提案の実装成功率: 70%以上
- 平均品質スコア: 7.0以上
- 改善効果の測定可能率: 80%以上

### 定性的指標
- 改善提案の具体性向上
- 実装手順の明確性
- フィードバックに基づく継続改善

---

**作成日**: 2025-08-02  
**ステータス**: Ready for Implementation  
**前提条件**: タスク1, 2完了  
**技術要件**: Python開発経験、YAML理解、テスト作成能力