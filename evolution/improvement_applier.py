"""
進化改善適用器
解析された改善を知識ファイルとYAML設定に適用
"""

import os
import yaml
import re
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ImprovementApplier:
    """進化改善をシステムファイルに適用"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.backup_dir = self.base_path / "evolution" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def apply_changes(
        self,
        changes: List[Tuple[str, str, Dict[str, Any]]],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        ファイルに変更リストを適用
        
        Args:
            changes: (file_path, action, changes)タプルのリスト
            dry_run: Trueの場合、変更をシミュレートのみ
            
        Returns:
            各変更の結果を含む辞書
        """
        results = {
            "applied": [],
            "failed": [],
            "skipped": []
        }
        
        for file_path, action, change_data in changes:
            try:
                result = self._apply_single_change(
                    file_path,
                    action,
                    change_data,
                    dry_run
                )
                
                if result["status"] == "applied":
                    results["applied"].append(result)
                elif result["status"] == "failed":
                    results["failed"].append(result)
                else:
                    results["skipped"].append(result)
                    
            except Exception as e:
                logger.error(
                    "Failed to apply change",
                    file=file_path,
                    action=action,
                    error=str(e)
                )
                results["failed"].append({
                    "file": file_path,
                    "action": action,
                    "error": str(e),
                    "status": "failed"
                })
        
        logger.info(
            "Changes applied",
            applied=len(results["applied"]),
            failed=len(results["failed"]),
            skipped=len(results["skipped"]),
            dry_run=dry_run
        )
        
        return results
    
    def _apply_single_change(
        self,
        file_path: str,
        action: str,
        change_data: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """ファイルに単一の変更を適用"""
        full_path = self.base_path / file_path
        
        # ファイルが存在する場合はバックアップを作成
        if full_path.exists() and not dry_run:
            self._create_backup(full_path)
        
        # アクションに基づいて変更を適用
        if action == "add":
            return self._apply_add(full_path, change_data, dry_run)
        elif action == "update":
            return self._apply_update(full_path, change_data, dry_run)
        elif action == "update_field":
            return self._apply_update_field(full_path, change_data, dry_run)
        elif action == "remove":
            return self._apply_remove(full_path, change_data, dry_run)
        else:
            return {
                "file": file_path,
                "action": action,
                "status": "skipped",
                "reason": f"Unknown action: {action}"
            }
    
    def _apply_add(
        self,
        file_path: Path,
        change_data: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """ファイルにコンテンツを追加"""
        content = change_data.get("content", "")
        
        if not content:
            return {
                "file": str(file_path),
                "action": "add",
                "status": "skipped",
                "reason": "No content provided"
            }
        
        try:
            if file_path.suffix == ".md":
                # Markdownファイルの場合、コンテンツを追加
                existing = ""
                if file_path.exists():
                    existing = file_path.read_text(encoding="utf-8")
                
                # タイムスタンプとソースを追加
                new_content = f"\n\n## Evolution Update - {datetime.now().isoformat()}\n\n{content}\n"
                
                if not dry_run:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(existing + new_content, encoding="utf-8")
                
                return {
                    "file": str(file_path),
                    "action": "add",
                    "status": "applied",
                    "content_added": len(new_content)
                }
                
            elif file_path.suffix == ".yaml":
                # YAMLファイルの場合、コンテンツをマージ
                return self._apply_yaml_add(file_path, content, dry_run)
                
        except Exception as e:
            return {
                "file": str(file_path),
                "action": "add",
                "status": "failed",
                "error": str(e)
            }
    
    def _apply_update(
        self,
        file_path: Path,
        change_data: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """ファイルのコンテンツを更新"""
        change = change_data.get("change", "")
        
        if not change:
            return {
                "file": str(file_path),
                "action": "update",
                "status": "skipped",
                "reason": "No change specified"
            }
        
        try:
            if not file_path.exists():
                return {
                    "file": str(file_path),
                    "action": "update",
                    "status": "skipped",
                    "reason": "File does not exist"
                }
            
            content = file_path.read_text(encoding="utf-8")
            
            # ファイルタイプに基づいてインテリジェントな更新を適用
            if file_path.suffix == ".md":
                # Markdownの場合、新しいセクションとして追加
                new_content = content + f"\n\n## Update - {datetime.now().isoformat()}\n\n{change}\n"
            else:
                # その他のファイルの場合、関連セクションを検索して置換
                new_content = self._intelligent_update(content, change)
            
            if not dry_run and new_content != content:
                file_path.write_text(new_content, encoding="utf-8")
            
            return {
                "file": str(file_path),
                "action": "update",
                "status": "applied" if new_content != content else "skipped",
                "changes": len(new_content) - len(content)
            }
            
        except Exception as e:
            return {
                "file": str(file_path),
                "action": "update",
                "status": "failed",
                "error": str(e)
            }
    
    def _apply_update_field(
        self,
        file_path: Path,
        change_data: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """YAMLファイルの特定フィールドを更新"""
        field = change_data.get("field", "")
        value = change_data.get("value")
        
        if not field:
            return {
                "file": str(file_path),
                "action": "update_field",
                "status": "skipped",
                "reason": "No field specified"
            }
        
        try:
            if not file_path.exists():
                return {
                    "file": str(file_path),
                    "action": "update_field",
                    "status": "skipped",
                    "reason": "File does not exist"
                }
            
            if file_path.suffix != ".yaml":
                return {
                    "file": str(file_path),
                    "action": "update_field",
                    "status": "skipped",
                    "reason": "Not a YAML file"
                }
            
            # YAMLをロード
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            # フィールドを更新（ドット表記でネストされたフィールドをサポート）
            self._update_nested_field(data, field, value)
            
            if not dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            return {
                "file": str(file_path),
                "action": "update_field",
                "status": "applied",
                "field": field,
                "new_value": value
            }
            
        except Exception as e:
            return {
                "file": str(file_path),
                "action": "update_field",
                "status": "failed",
                "error": str(e)
            }
    
    def _apply_remove(
        self,
        file_path: Path,
        change_data: Dict[str, Any],
        dry_run: bool
    ) -> Dict[str, Any]:
        """ファイルからコンテンツを削除"""
        pattern = change_data.get("pattern", "")
        
        if not pattern:
            return {
                "file": str(file_path),
                "action": "remove",
                "status": "skipped",
                "reason": "No pattern specified"
            }
        
        try:
            if not file_path.exists():
                return {
                    "file": str(file_path),
                    "action": "remove",
                    "status": "skipped",
                    "reason": "File does not exist"
                }
            
            content = file_path.read_text(encoding="utf-8")
            new_content = re.sub(pattern, "", content, flags=re.MULTILINE)
            
            if not dry_run and new_content != content:
                file_path.write_text(new_content, encoding="utf-8")
            
            return {
                "file": str(file_path),
                "action": "remove",
                "status": "applied" if new_content != content else "skipped",
                "removed_chars": len(content) - len(new_content)
            }
            
        except Exception as e:
            return {
                "file": str(file_path),
                "action": "remove",
                "status": "failed",
                "error": str(e)
            }
    
    def _apply_yaml_add(self, file_path: Path, content: str, dry_run: bool) -> Dict[str, Any]:
        """YAMLファイルにコンテンツを追加"""
        try:
            # コンテンツをYAMLとして解析を試みる
            new_data = yaml.safe_load(content)
            
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_data = yaml.safe_load(f) or {}
            else:
                existing_data = {}
            
            # データをマージ
            if isinstance(new_data, dict) and isinstance(existing_data, dict):
                merged_data = self._deep_merge(existing_data, new_data)
            else:
                # 辞書以外のデータはマージできない
                return {
                    "file": str(file_path),
                    "action": "add",
                    "status": "skipped",
                    "reason": "辞書以外のYAMLデータはマージできません"
                }
            
            if not dry_run:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    yaml.dump(merged_data, f, default_flow_style=False, allow_unicode=True)
            
            return {
                "file": str(file_path),
                "action": "add",
                "status": "applied",
                "keys_added": len(new_data.keys()) if isinstance(new_data, dict) else 0
            }
            
        except yaml.YAMLError:
            # 有効なYAMLでない場合、テキストとして扱いコメントとして追加
            if not dry_run:
                if file_path.exists():
                    existing = file_path.read_text(encoding="utf-8")
                else:
                    existing = ""
                
                new_content = existing + f"\n# Evolution update: {content}\n"
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(new_content, encoding="utf-8")
            
            return {
                "file": str(file_path),
                "action": "add",
                "status": "applied",
                "added_as_comment": True
            }
    
    def _intelligent_update(self, content: str, change: str) -> str:
        """コンテンツにインテリジェントな更新を適用"""
        # これはシンプルな実装 - NLPで強化可能
        
        # 変更内のキーワードを探す
        keywords = re.findall(r'\b(?:update|change|modify|replace)\s+(\w+)', change, re.IGNORECASE)
        
        for keyword in keywords:
            # 関連セクションを検索して更新を試みる
            pattern = rf'({keyword}.*?)(?=\n\n|\Z)'
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                content = re.sub(
                    pattern,
                    f"\\1\n# Updated: {change}",
                    content,
                    flags=re.IGNORECASE | re.DOTALL
                )
                return content
        
        # 特定のセクションが見つからない場合、コメントとして追加
        return content + f"\n# Evolution suggestion: {change}\n"
    
    def _update_nested_field(self, data: Dict[str, Any], field: str, value: Any) -> None:
        """辞書内のネストされたフィールドを更新"""
        parts = field.split(".")
        current = data
        
        # ターゲットフィールドの親に移動
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # 値を設定
        current[parts[-1]] = value
    
    def _deep_merge(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """2つの辞書をディープマージ"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _create_backup(self, file_path: Path) -> Path:
        """ファイルのバックアップを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name
        
        # ファイルをバックアップにコピー
        backup_path.write_bytes(file_path.read_bytes())
        
        logger.info(
            "Created backup",
            original=str(file_path),
            backup=str(backup_path)
        )
        
        return backup_path
    
    def restore_backup(self, file_path: str, backup_time: Optional[str] = None) -> bool:
        """バックアップからファイルを復元"""
        try:
            full_path = self.base_path / file_path
            backups = list(self.backup_dir.glob(f"{full_path.name}.*.bak"))
            
            if not backups:
                logger.warning("No backups found", file=file_path)
                return False
            
            # タイムスタンプでソート
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # バックアップを選択
            if backup_time:
                # 時間に一致するバックアップを検索
                for backup in backups:
                    if backup_time in str(backup):
                        selected_backup = backup
                        break
                else:
                    logger.warning("No backup found for time", time=backup_time)
                    return False
            else:
                # 最新のものを使用
                selected_backup = backups[0]
            
            # 復元
            full_path.write_bytes(selected_backup.read_bytes())
            
            logger.info(
                "Restored from backup",
                file=file_path,
                backup=str(selected_backup)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to restore backup",
                file=file_path,
                error=str(e)
            )
            return False