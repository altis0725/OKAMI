# タスク 2.5: Evolution Systemファイル更新バグ修正

## 概要
Evolution Systemが生成する改善提案ファイルが実際に作成・更新されない問題を修正します。

## 問題の症状
- Evolution Crewの実行ログには「ファイルを更新しました」と表示される
- 実際には`knowledge/optimization_best_practices.md`等のファイルが存在しない
- Docker環境で特に頻繁に発生

## 目標
- [ ] ファイル更新処理の問題箇所を特定
- [ ] ファイル作成・更新を確実に実行する実装
- [ ] 適切なエラーハンドリングとログ出力
- [ ] Docker環境での動作保証

## 実装手順

### Step 1: 問題診断と現状調査

#### 1.1 ImprovementApplierの動作確認
```python
# evolution/improvement_applier.py の調査ポイント
class ImprovementApplier:
    def apply_knowledge_update(self, update: Dict[str, Any]) -> bool:
        # ファイルパスの解決方法を確認
        # ディレクトリ作成の有無を確認
        # エラーハンドリングの確認
```

#### 1.2 ログ出力の追加
```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def apply_knowledge_update(self, update: Dict[str, Any]) -> bool:
    file_path = Path(update.get("file_path", ""))
    logger.info(f"Attempting to update file: {file_path}")
    logger.info(f"Absolute path: {file_path.absolute()}")
    logger.info(f"File exists: {file_path.exists()}")
    logger.info(f"Parent exists: {file_path.parent.exists()}")
```

### Step 2: パス解決の修正

#### 2.1 プロジェクトルートの取得
```python
from pathlib import Path

class ImprovementApplier:
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.knowledge_dir = self.project_root / "knowledge"
        
    def resolve_file_path(self, file_path: str) -> Path:
        """ファイルパスを解決し、絶対パスを返す"""
        path = Path(file_path)
        
        # 相対パスの場合はプロジェクトルートからの相対パスとして解決
        if not path.is_absolute():
            path = self.project_root / path
            
        return path.resolve()
```

#### 2.2 ディレクトリの自動作成
```python
def ensure_parent_directory(self, file_path: Path) -> bool:
    """親ディレクトリが存在しない場合は作成"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured parent directory exists: {file_path.parent}")
        return True
    except Exception as e:
        logger.error(f"Failed to create parent directory: {e}")
        return False
```

### Step 3: ファイル更新処理の改善

#### 3.1 安全なファイル書き込み
```python
def safe_write_file(self, file_path: Path, content: str, backup: bool = True) -> bool:
    """ファイルを安全に書き込む"""
    try:
        # バックアップの作成
        if backup and file_path.exists():
            backup_path = self.create_backup(file_path)
            logger.info(f"Created backup: {backup_path}")
        
        # 親ディレクトリの確認と作成
        if not self.ensure_parent_directory(file_path):
            return False
        
        # ファイルの書き込み
        file_path.write_text(content, encoding='utf-8')
        
        # 書き込み結果の検証
        if not file_path.exists():
            logger.error(f"File was not created: {file_path}")
            return False
            
        actual_content = file_path.read_text(encoding='utf-8')
        if actual_content != content:
            logger.error(f"File content mismatch: {file_path}")
            return False
            
        logger.info(f"Successfully wrote file: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return False
```

### Step 4: Docker環境対応

#### 4.1 権限の確認と修正
```python
import os
import stat

def check_and_fix_permissions(self, file_path: Path) -> bool:
    """ファイルの権限を確認し、必要に応じて修正"""
    try:
        # Dockerコンテナ内のユーザーIDを取得
        uid = os.getuid()
        gid = os.getgid()
        
        # ファイルが存在する場合は権限を確認
        if file_path.exists():
            stat_info = file_path.stat()
            if stat_info.st_uid != uid:
                logger.warning(f"File owner mismatch: {file_path}")
                # 可能であれば所有者を変更
                try:
                    os.chown(file_path, uid, gid)
                except PermissionError:
                    logger.warning("Cannot change file ownership")
        
        # 書き込み権限を確認
        parent = file_path.parent
        if not os.access(parent, os.W_OK):
            logger.error(f"No write permission for: {parent}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Permission check failed: {e}")
        return False
```

### Step 5: 統合実装

#### 5.1 改善されたapply_knowledge_update
```python
def apply_knowledge_update(self, update: Dict[str, Any]) -> bool:
    """知識ファイルの更新を適用"""
    try:
        # 入力検証
        if not update or "file_path" not in update:
            logger.error("Invalid update: missing file_path")
            return False
            
        if "content" not in update and "updates" not in update:
            logger.error("Invalid update: missing content or updates")
            return False
        
        # パス解決
        file_path = self.resolve_file_path(update["file_path"])
        logger.info(f"Processing file update: {file_path}")
        
        # 権限確認
        if not self.check_and_fix_permissions(file_path):
            return False
        
        # コンテンツの準備
        if "content" in update:
            content = update["content"]
        else:
            # 既存ファイルの読み込みと更新
            if file_path.exists():
                content = file_path.read_text(encoding='utf-8')
            else:
                content = ""
            
            # updatesの適用
            for change in update.get("updates", []):
                content = self.apply_change(content, change)
        
        # ファイル書き込み
        success = self.safe_write_file(file_path, content)
        
        # 結果の記録
        if success:
            self.record_successful_update(file_path, update)
        else:
            self.record_failed_update(file_path, update)
            
        return success
        
    except Exception as e:
        logger.error(f"Unexpected error in apply_knowledge_update: {e}")
        return False
```

### Step 6: テストの実装

#### 6.1 単体テスト
```python
# tests/test_evolution_file_update.py
import pytest
from pathlib import Path
from evolution.improvement_applier import ImprovementApplier

def test_file_creation(tmp_path):
    """新規ファイルの作成テスト"""
    applier = ImprovementApplier(project_root=tmp_path)
    
    update = {
        "file_path": "knowledge/test_file.md",
        "content": "# Test Content\nThis is a test."
    }
    
    result = applier.apply_knowledge_update(update)
    assert result is True
    
    file_path = tmp_path / "knowledge" / "test_file.md"
    assert file_path.exists()
    assert file_path.read_text() == "# Test Content\nThis is a test."

def test_file_update(tmp_path):
    """既存ファイルの更新テスト"""
    # 既存ファイルを作成
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    existing_file = knowledge_dir / "existing.md"
    existing_file.write_text("Original content")
    
    applier = ImprovementApplier(project_root=tmp_path)
    
    update = {
        "file_path": "knowledge/existing.md",
        "content": "Updated content"
    }
    
    result = applier.apply_knowledge_update(update)
    assert result is True
    assert existing_file.read_text() == "Updated content"
```

#### 6.2 Docker環境での統合テスト
```bash
# Docker環境でのテスト実行スクリプト
#!/bin/bash

# テスト用のDockerコンテナを起動
docker-compose up -d

# コンテナ内でテストを実行
docker-compose exec okami python -m pytest tests/test_evolution_file_update.py -v

# ファイル作成の確認
docker-compose exec okami ls -la knowledge/

# Evolution Crewの実行テスト
docker-compose exec okami python -c "
from crews.crew_factory import CrewFactory
factory = CrewFactory()
crew = factory.create_crew('evolution_crew')
result = crew.kickoff({'topic': 'test improvement'})
"

# 生成されたファイルの確認
docker-compose exec okami find knowledge/ -type f -name "*.md" -mmin -5

# クリーンアップ
docker-compose down
```

### Step 7: ログとモニタリングの改善

#### 7.1 詳細なログ設定
```python
# evolution/improvement_applier.py
import logging
from datetime import datetime

# ログフォーマットの改善
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evolution_file_updates.log'),
        logging.StreamHandler()
    ]
)

class FileUpdateLogger:
    """ファイル更新操作の詳細ログ"""
    
    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or Path("logs/evolution")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def log_update_attempt(self, file_path: Path, update: Dict):
        """更新試行のログ"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "update_attempt",
            "file_path": str(file_path),
            "update": update,
            "file_exists_before": file_path.exists()
        }
        self._write_log(log_entry)
        
    def log_update_result(self, file_path: Path, success: bool, error: str = None):
        """更新結果のログ"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "update_result",
            "file_path": str(file_path),
            "success": success,
            "file_exists_after": file_path.exists(),
            "error": error
        }
        self._write_log(log_entry)
```

## 実装チェックリスト

- [ ] Step 1: 問題診断と現状調査
  - [ ] ImprovementApplierのコード確認
  - [ ] ログ出力の追加
  - [ ] 問題箇所の特定

- [ ] Step 2: パス解決の修正
  - [ ] プロジェクトルートの適切な取得
  - [ ] 相対パス/絶対パスの処理
  - [ ] ディレクトリの自動作成

- [ ] Step 3: ファイル更新処理の改善
  - [ ] 安全なファイル書き込み実装
  - [ ] バックアップ機能
  - [ ] 書き込み結果の検証

- [ ] Step 4: Docker環境対応
  - [ ] 権限の確認と修正
  - [ ] コンテナ内での動作確認
  - [ ] ボリュームマウントの検証

- [ ] Step 5: 統合実装
  - [ ] 改善されたapply_knowledge_update
  - [ ] エラーハンドリング
  - [ ] 結果の記録

- [ ] Step 6: テストの実装
  - [ ] 単体テスト作成
  - [ ] Docker環境での統合テスト
  - [ ] CI/CDパイプラインへの組み込み

- [ ] Step 7: ログとモニタリング
  - [ ] 詳細なログ実装
  - [ ] 監視ポイントの設置
  - [ ] デバッグ情報の充実

## 成功基準

1. **機能要件**
   - Evolution Systemが提案したファイルが実際に作成される
   - 既存ファイルの更新が正しく反映される
   - ログメッセージと実際の動作が一致する

2. **非機能要件**
   - Docker環境でも正常に動作する
   - エラー時に適切なログが出力される
   - ファイル操作の失敗時にシステムがクラッシュしない

3. **テスト要件**
   - すべての単体テストがパスする
   - Docker環境での統合テストがパスする
   - 実際のEvolution Crew実行でファイルが作成される

## 関連ファイル

- `evolution/improvement_applier.py` - メイン修正対象
- `evolution/improvement_parser.py` - パーサーロジック
- `tests/test_evolution_file_update.py` - 新規テストファイル
- `docker-compose.yaml` - Docker設定
- `logs/evolution/` - ログ出力先

## 注意事項

1. **後方互換性**: 既存の動作を壊さないよう注意
2. **パフォーマンス**: ファイル操作の効率性を維持
3. **セキュリティ**: ファイルパスのサニタイズを実施
4. **エラー処理**: すべての例外を適切にキャッチ

---
**タスクID**: TASK-002.5
**優先度**: 緊急
**推定時間**: 2-3時間
**前提条件**: Phase 2完了
**次のステップ**: Phase 3への移行