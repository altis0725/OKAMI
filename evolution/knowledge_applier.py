"""知識管理に特化したEvolution System Applier"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import hashlib
import re

class KnowledgeApplier:
    """知識管理に特化したEvolution System Applier"""
    
    def __init__(self, knowledge_base_path: Path = Path("knowledge")):
        self.knowledge_base = knowledge_base_path
        self.knowledge_index = self._load_knowledge_index()
        self.backup_dir = Path("evolution/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def apply_knowledge_changes(self, changes: List[Dict], dry_run: bool = False):
        """知識変更の適用"""
        results = []
        
        for change in changes:
            if change["type"] == "add_knowledge":
                result = self._add_knowledge(change, dry_run)
            elif change["type"] == "update_knowledge":
                result = self._update_knowledge(change, dry_run)
            else:
                result = {"status": "skipped", "reason": f"Unknown type: {change['type']}"}
            
            results.append(result)
            
        # インデックスの更新
        if not dry_run:
            self._update_knowledge_index()
            
        return results
    
    def _add_knowledge(self, change: Dict, dry_run: bool) -> Dict:
        """新規知識の追加"""
        try:
            # カテゴリディレクトリの確保
            category = change.get("category", "general")
            category_path = self.knowledge_base / category
            
            if not dry_run:
                category_path.mkdir(parents=True, exist_ok=True)
            
            # 知識ファイルの作成
            # ファイル名を取得（パスの最後の部分）
            file_name = Path(change["file"]).name
            # カテゴリパスを基準にファイルパスを構築
            file_path = category_path / file_name
            
            # 構造化されたマークダウンの生成
            content = self._format_knowledge_content(
                title=change.get("title", "Untitled"),
                content=change["content"],
                tags=change.get("tags", []),
                created_at=datetime.now()
            )
            
            if not dry_run:
                # ファイルが既に存在する場合はスキップ
                if file_path.exists():
                    # 内容をチェックして重複判定
                    existing_content = file_path.read_text(encoding="utf-8").lower()
                    if change["content"].strip().lower() in existing_content:
                        return {
                            "status": "skipped",
                            "reason": "Duplicate knowledge detected - file already exists with similar content",
                            "file": str(file_path)
                        }
                
                # 重複チェック（生のコンテンツでチェック）
                if self._is_duplicate_knowledge_by_content(change["content"], change.get("title", ""), category):
                    return {
                        "status": "skipped",
                        "reason": "Duplicate knowledge detected",
                        "file": str(file_path)
                    }
                
                # ファイル書き込み
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
                
                # インデックスに追加
                self._add_to_index(file_path, change)
                
                print(f"✅ Created new knowledge file: {file_path}")
            
            return {
                "status": "success",
                "file": str(file_path),
                "category": category,
                "dry_run": dry_run
            }
            
        except Exception as e:
            return {
                "status": "error",
                "reason": str(e),
                "file": change.get("file", "unknown")
            }
    
    def _update_knowledge(self, change: Dict, dry_run: bool) -> Dict:
        """既存知識の更新"""
        try:
            # ファイルパスを解決
            # knowledge/カテゴリ/ファイル名 という形式を想定
            file_path_parts = Path(change["file"]).parts
            if len(file_path_parts) >= 2 and file_path_parts[0] == "knowledge":
                # knowledge/以下のパスを取得
                relative_parts = file_path_parts[1:]
                file_path = self.knowledge_base.joinpath(*relative_parts)
            else:
                # それ以外の場合は、ファイル名のみを使用し、カテゴリを検出
                file_name = Path(change["file"]).name
                category = self._detect_category_from_path(change["file"])
                file_path = self.knowledge_base / category / file_name
            
            if not file_path.exists():
                # ファイルが存在しない場合は新規作成として扱う
                return self._add_knowledge({
                    **change,
                    "type": "add_knowledge",
                    "title": change.get("section", "Knowledge Update").replace("#", "").strip(),
                    "category": self._detect_category_from_path(str(file_path))
                }, dry_run)
            
            current_content = file_path.read_text(encoding="utf-8")
            
            # 更新操作の実行
            operation = change.get("operation", "append")
            section = change.get("section")
            new_content = change["content"]
            
            if operation == "append":
                updated_content = self._append_to_section(
                    current_content, section, new_content
                )
            elif operation == "replace":
                updated_content = self._replace_section(
                    current_content, section, new_content
                )
            elif operation == "insert":
                updated_content = self._insert_at_section(
                    current_content, section, new_content
                )
            else:
                return {
                    "status": "error",
                    "reason": f"Unknown operation: {operation}",
                    "file": str(file_path)
                }
            
            if not dry_run:
                # バックアップ作成
                backup_path = self.backup_dir / f"{file_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                backup_path.write_text(current_content, encoding="utf-8")
                
                # 更新内容の書き込み
                file_path.write_text(updated_content, encoding="utf-8")
                
                # インデックスの更新
                self._update_in_index(file_path, change)
                
                print(f"✅ Updated knowledge file: {file_path}")
            
            return {
                "status": "success",
                "file": str(file_path),
                "operation": operation,
                "dry_run": dry_run
            }
            
        except Exception as e:
            return {
                "status": "error",
                "reason": str(e),
                "file": change.get("file", "unknown")
            }
    
    def _format_knowledge_content(
        self, 
        title: str, 
        content: str, 
        tags: List[str], 
        created_at: datetime
    ) -> str:
        """知識コンテンツのフォーマット"""
        formatted = f"""# {title}

**Created**: {created_at.strftime('%Y-%m-%d %H:%M:%S')}  
**Tags**: {', '.join(tags) if tags else 'None'}  
**Category**: Knowledge Base

---

{content}

---

## Metadata

- **Source**: Evolution System
- **Version**: 1.0
- **Last Updated**: {created_at.strftime('%Y-%m-%d %H:%M:%S')}

## Related Knowledge

<!-- Automatically populated by Knowledge Manager -->

## Usage Examples

<!-- To be added as the knowledge is applied -->
"""
        return formatted
    
    def _is_duplicate_knowledge_by_content(self, raw_content: str, title: str, category: str) -> bool:
        """生のコンテンツで重複知識をチェック"""
        category_path = self.knowledge_base / category
        
        if not category_path.exists():
            return False
        
        # 正規化
        normalized_content = raw_content.strip().lower()
        normalized_title = title.strip().lower()
        
        for file in category_path.glob("*.md"):
            existing_content = file.read_text(encoding="utf-8").lower()
            
            # タイトルとコンテンツ両方が既存ファイルに含まれているかチェック
            if normalized_title and normalized_content:
                if normalized_title in existing_content and normalized_content in existing_content:
                    return True
        
        return False
    
    def _detect_category_from_path(self, file_path: str) -> str:
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
    
    def _load_knowledge_index(self) -> Dict:
        """知識インデックスの読み込み"""
        index_path = self.knowledge_base / "index.json"
        
        if index_path.exists():
            try:
                return json.loads(index_path.read_text(encoding="utf-8"))
            except:
                pass
        
        return {
            "files": {},
            "tags": {},
            "categories": {},
            "last_updated": datetime.now().isoformat()
        }
    
    def _update_knowledge_index(self):
        """知識インデックスの更新"""
        index_path = self.knowledge_base / "index.json"
        self.knowledge_index["last_updated"] = datetime.now().isoformat()
        index_path.write_text(
            json.dumps(self.knowledge_index, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def _add_to_index(self, file_path: Path, change: Dict):
        """インデックスへの追加"""
        # インデックスには相対パスを保存（knowledge_baseからの相対パス）
        try:
            relative_path = file_path.relative_to(self.knowledge_base.parent)
        except ValueError:
            # 相対パスを取得できない場合は絶対パスを使用
            relative_path = file_path
        
        self.knowledge_index["files"][str(relative_path)] = {
            "title": change.get("title", "Untitled"),
            "category": change.get("category", "general"),
            "tags": change.get("tags", []),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # タグインデックスの更新
        for tag in change.get("tags", []):
            if tag not in self.knowledge_index["tags"]:
                self.knowledge_index["tags"][tag] = []
            self.knowledge_index["tags"][tag].append(str(relative_path))
        
        # カテゴリインデックスの更新
        category = change.get("category", "general")
        if category not in self.knowledge_index["categories"]:
            self.knowledge_index["categories"][category] = []
        self.knowledge_index["categories"][category].append(str(relative_path))
    
    def _update_in_index(self, file_path: Path, change: Dict):
        """インデックスの更新"""
        if str(file_path) in self.knowledge_index["files"]:
            self.knowledge_index["files"][str(file_path)]["updated_at"] = \
                datetime.now().isoformat()
    
    def _append_to_section(self, content: str, section: Optional[str], new_text: str) -> str:
        """セクションへの追記"""
        if section:
            lines = content.split('\n')
            section_index = -1
            
            # セクションを探す
            for i, line in enumerate(lines):
                if section in line:
                    section_index = i
                    break
            
            if section_index >= 0:
                # セクションの終わりを見つける
                next_section_index = len(lines)
                section_level = len(section.split()[0])  # #の数を数える
                
                for i in range(section_index + 1, len(lines)):
                    if lines[i].strip().startswith('#'):
                        # 同じレベルまたは上位のセクションを見つけたら終了
                        current_level = len(lines[i].strip().split()[0])
                        if current_level <= section_level:
                            next_section_index = i
                            break
                
                # セクションの最後に追加（空行を入れて）
                insert_index = next_section_index
                # 既存の空行をスキップ
                while insert_index > section_index + 1 and not lines[insert_index - 1].strip():
                    insert_index -= 1
                
                lines.insert(insert_index, "")
                lines.insert(insert_index + 1, new_text)
                return '\n'.join(lines)
        
        # セクションが見つからない場合は末尾に追加
        return content.rstrip() + '\n\n' + new_text
    
    def _replace_section(self, content: str, section: Optional[str], new_text: str) -> str:
        """セクションの置換"""
        if not section:
            return new_text
        
        lines = content.split('\n')
        section_start = -1
        section_end = len(lines)
        
        # セクションを探す
        for i, line in enumerate(lines):
            if section in line:
                section_start = i
                section_level = len(section.split()[0])  # #の数を数える
                
                # 次のセクションを探す
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith('#'):
                        current_level = len(lines[j].strip().split()[0])
                        if current_level <= section_level:
                            section_end = j
                            break
                break
        
        if section_start >= 0:
            # セクションヘッダーは保持して、内容だけを置換
            new_lines = lines[:section_start + 1] + ["", new_text] + lines[section_end:]
            return '\n'.join(new_lines)
        
        return content
    
    def _insert_at_section(self, content: str, section: Optional[str], new_text: str) -> str:
        """セクションへの挿入"""
        if section:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if section in line:
                    # セクションヘッダーの直後に挿入
                    lines.insert(i + 1, "")
                    lines.insert(i + 2, new_text)
                    return '\n'.join(lines)
        
        # セクションが見つからない場合は先頭に挿入
        return new_text + '\n\n' + content

    def get_knowledge_stats(self) -> Dict:
        """知識統計の取得"""
        stats = {
            "total_files": len(self.knowledge_index.get("files", {})),
            "categories": {},
            "tags": {},
            "last_updated": self.knowledge_index.get("last_updated", "Unknown")
        }
        
        # カテゴリ別の統計
        for category, files in self.knowledge_index.get("categories", {}).items():
            stats["categories"][category] = len(files)
        
        # タグ別の統計
        for tag, files in self.knowledge_index.get("tags", {}).items():
            stats["tags"][tag] = len(files)
        
        return stats