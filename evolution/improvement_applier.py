"""
進化改善適用器
解析された改善を知識ファイルとYAML設定に適用
"""

import os
import yaml
import re
import json
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime
import structlog
import traceback
from evolution.knowledge_applier import KnowledgeApplier

logger = structlog.get_logger()


class ImprovementApplier:
    """進化改善をシステムファイルに適用"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.backup_dir = self.base_path / "evolution" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        # 知識管理専用Applierのインスタンス化
        self.knowledge_applier = KnowledgeApplier(self.base_path / "knowledge")
    
    def apply_changes(
        self,
        changes: List[Tuple[str, str, Dict[str, Any]]],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        ファイルに変更リストを適用
        注: knowledgeディレクトリのファイルのみが変更対象となります。
        
        Args:
            changes: (file_path, action, changes)タプルのリスト
            dry_run: Trueの場合、変更をシミュレートのみ
            
        Returns:
            各変更の結果を含む辞書
        """
        results = {
            "applied": [],
            "failed": [],
            "skipped": [],
            "blocked_config_changes": []  # ブロックされたconfig変更を記録
        }
        
        # 提案されたconfig変更を保存するリスト
        proposed_config_changes = []
        
        # 知識関連の変更のみを処理
        knowledge_changes = []
        
        for file_path, action, change_data in changes:
            if file_path.startswith("knowledge/"):
                # 知識ファイルの変更はKnowledgeApplierに委譲
                knowledge_changes.append((file_path, action, change_data))
            else:
                # knowledge以外のファイルへの変更はブロック
                blocked_change = {
                    "file": file_path,
                    "action": action,
                    "changes": change_data,
                    "status": "blocked",
                    "reason": "Only knowledge directory files can be modified"
                }
                results["blocked_config_changes"].append(blocked_change)
                results["skipped"].append(blocked_change)
                
                # config変更の場合は提案として記録
                if file_path.startswith("config/"):
                    proposed_config_changes.append({
                        "file_path": file_path,
                        "action": action,
                        "changes": change_data,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                logger.warning(
                    "Blocked non-knowledge file modification",
                    file=file_path,
                    action=action,
                    reason="Only knowledge directory files can be modified"
                )
        
        # 知識変更の処理
        if knowledge_changes:
            knowledge_results = self._apply_knowledge_changes(knowledge_changes, dry_run)
            results["applied"].extend(knowledge_results.get("applied", []))
            results["failed"].extend(knowledge_results.get("failed", []))
            results["skipped"].extend(knowledge_results.get("skipped", []))
        
        # 提案されたconfig変更をファイルに保存
        if proposed_config_changes and not dry_run:
            self._save_proposed_config_changes(proposed_config_changes)
        
        logger.info(
            "Changes applied",
            applied=len(results["applied"]),
            failed=len(results["failed"]),
            skipped=len(results["skipped"]),
            blocked=len(results["blocked_config_changes"]),
            dry_run=dry_run
        )
        
        return results
    
    def _apply_knowledge_changes(
        self,
        knowledge_changes: List[Tuple[str, str, Dict[str, Any]]],
        dry_run: bool
    ) -> Dict[str, Any]:
        """知識関連の変更をKnowledgeApplierで処理"""
        results = {
            "applied": [],
            "failed": [],
            "skipped": []
        }
        
        # KnowledgeApplier用のフォーマットに変換
        formatted_changes = []
        for file_path, action, change_data in knowledge_changes:
            if action == "add":
                formatted_change = {
                    "type": "add_knowledge",
                    "file": file_path,
                    "content": change_data.get("content", ""),
                    "category": self._detect_category(file_path),
                    "title": change_data.get("title", self._extract_title(change_data.get("content", ""))),
                    "tags": change_data.get("tags", []),
                    "reason": change_data.get("reason", "Added by Evolution System")
                }
            elif action == "update":
                formatted_change = {
                    "type": "update_knowledge",
                    "file": file_path,
                    "content": change_data.get("change", change_data.get("content", "")),
                    "section": change_data.get("section"),
                    "operation": "append",
                    "reason": change_data.get("reason", "Updated by Evolution System")
                }
            else:
                continue
            
            formatted_changes.append(formatted_change)
        
        # KnowledgeApplierで処理
        if formatted_changes:
            applier_results = self.knowledge_applier.apply_knowledge_changes(formatted_changes, dry_run)
            
            # 結果を統合
            for result in applier_results:
                if result["status"] == "success":
                    results["applied"].append(result)
                elif result["status"] == "error":
                    results["failed"].append(result)
                else:
                    results["skipped"].append(result)
        
        return results
    
    def _detect_category(self, file_path: str) -> str:
        """ファイルパスからカテゴリを検出"""
        if "agents" in file_path:
            return "agents"
        elif "crew" in file_path:
            return "crew"
        elif "system" in file_path:
            return "system"
        elif "domain" in file_path:
            return "domain"
        else:
            return "general"
    
    def _extract_title(self, content: str) -> str:
        """コンテンツからタイトルを抽出"""
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                # 最初の非空行をタイトルとして使用
                return line.strip()[:50]  # 最大50文字
        return "Untitled Knowledge"
    
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
        
        # contentがファイルパスのように見える場合の処理
        # (例: "file": "knowledge/xxx.md" という文字列が誤ってcontentとして渡される場合)
        if content.startswith('"file"'):
            logger.warning(
                "Content looks like a file path, skipping",
                file=str(file_path),
                content=content[:100]
            )
            return {
                "file": str(file_path),
                "action": "add",
                "status": "skipped",
                "reason": "Content appears to be a file path, not actual content"
            }
        
        try:
            # general.mdへの更新はevolution履歴用のファイルにリダイレクト
            if file_path.name == "general.md" and "Evolution Update" in content:
                # Evolution履歴専用ファイルにリダイレクト
                file_path = file_path.parent / "evolution_history.md"
                logger.info("Redirecting evolution history to dedicated file", file=str(file_path))
            
            if file_path.suffix == ".md":
                # Markdownファイルの場合
                existing = ""
                is_new_file = False
                
                if file_path.exists():
                    existing = file_path.read_text(encoding="utf-8")
                else:
                    is_new_file = True
                    # ディレクトリが存在しない場合は作成
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                
                if is_new_file:
                    # 新しいファイルを作成
                    if file_path.name == "evolution_history.md":
                        # Evolution履歴ファイルの場合
                        new_content = f"""# OKAMI Evolution History

This file contains the evolution history of the OKAMI system.
Each entry represents an improvement or change made by the Evolution System.

---

## Evolution Update - {datetime.now().isoformat()}

{content}

---
*Generated by OKAMI Evolution System*
"""
                    else:
                        # 通常の新規ファイル
                        new_content = f"# {file_path.stem.replace('_', ' ').title()}\n\n{content}\n\n---\n*Generated by OKAMI Evolution System on {datetime.now().isoformat()}*\n"
                    
                    if not dry_run:
                        file_path.write_text(new_content, encoding="utf-8")
                        logger.info(
                            "Created new file",
                            file=str(file_path),
                            size=len(new_content)
                        )
                    
                    return {
                        "file": str(file_path),
                        "action": "add",
                        "status": "applied",
                        "content_added": len(new_content),
                        "new_file": True
                    }
                else:
                    # 既存ファイルに追記
                    new_content = f"\n\n## Evolution Update - {datetime.now().isoformat()}\n\n{content}\n"
                    
                    if not dry_run:
                        file_path.write_text(existing + new_content, encoding="utf-8")
                        logger.info(
                            "Updated existing file",
                            file=str(file_path),
                            content_added=len(new_content)
                        )
                    
                    return {
                        "file": str(file_path),
                        "action": "add",
                        "status": "applied",
                        "content_added": len(new_content),
                        "new_file": False
                    }
                
            elif file_path.suffix == ".yaml":
                # YAMLファイルの場合、コンテンツをマージ
                return self._apply_yaml_add(file_path, content, dry_run)
                
        except Exception as e:
            logger.error(
                "Failed to apply add",
                file=str(file_path),
                error=str(e),
                traceback=traceback.format_exc()
            )
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
    
    def _save_proposed_config_changes(self, changes: List[Dict[str, Any]]) -> None:
        """
        提案されたconfig変更を記録ファイルに保存
        
        Args:
            changes: 提案された変更のリスト
        """
        try:
            # 提案ファイルのパス
            proposals_dir = self.base_path / "evolution" / "proposed_changes"
            proposals_dir.mkdir(parents=True, exist_ok=True)
            
            # 既存の提案を読み込み
            proposals_file = proposals_dir / "config_proposals.json"
            if proposals_file.exists():
                with open(proposals_file, "r", encoding="utf-8") as f:
                    existing_proposals = json.load(f)
            else:
                existing_proposals = []
            
            # 新しい提案を追加
            existing_proposals.extend(changes)
            
            # ファイルに保存
            with open(proposals_file, "w", encoding="utf-8") as f:
                json.dump(existing_proposals, f, indent=2, ensure_ascii=False)
            
            logger.info(
                "Saved proposed config changes",
                count=len(changes),
                file=str(proposals_file)
            )
            
        except Exception as e:
            logger.error(
                "Failed to save proposed config changes",
                error=str(e)
            )
    
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