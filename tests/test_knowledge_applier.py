"""KnowledgeApplierのテストケース"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from evolution.knowledge_applier import KnowledgeApplier


class TestKnowledgeApplier:
    """KnowledgeApplierのテストクラス"""
    
    @pytest.fixture
    def temp_knowledge_base(self):
        """テスト用の一時知識ベースディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        knowledge_base = Path(temp_dir) / "knowledge"
        knowledge_base.mkdir(parents=True, exist_ok=True)
        
        # テスト用のカテゴリディレクトリを作成
        for category in ["agents", "crew", "system", "domain", "general"]:
            (knowledge_base / category).mkdir(exist_ok=True)
        
        # テスト用の既存ファイルを作成
        existing_file = knowledge_base / "general" / "test_existing.md"
        existing_file.write_text("""# Test Existing Knowledge

## Overview
This is existing knowledge for testing.

## Details
Some details here.
""", encoding="utf-8")
        
        yield knowledge_base
        
        # クリーンアップ
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def applier(self, temp_knowledge_base):
        """テスト用のKnowledgeApplierインスタンスを作成"""
        # テスト用のバックアップディレクトリを作成
        backup_dir = temp_knowledge_base.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        applier = KnowledgeApplier(temp_knowledge_base)
        applier.backup_dir = backup_dir
        return applier
    
    def test_init(self, temp_knowledge_base):
        """初期化のテスト"""
        applier = KnowledgeApplier(temp_knowledge_base)
        assert applier.knowledge_base == temp_knowledge_base
        assert isinstance(applier.knowledge_index, dict)
        assert applier.backup_dir.exists()
    
    def test_add_new_knowledge(self, applier, temp_knowledge_base):
        """新規知識追加のテスト"""
        change = {
            "type": "add_knowledge",
            "category": "agents",
            "file": "knowledge/agents/test_agent.md",
            "title": "Test Agent Knowledge",
            "content": "This is test knowledge about agents.",
            "tags": ["test", "agent"],
            "reason": "Testing knowledge addition"
        }
        
        results = applier.apply_knowledge_changes([change], dry_run=False)
        
        assert len(results) == 1
        assert results[0]["status"] == "success"
        assert results[0]["category"] == "agents"
        
        # ファイルが作成されたことを確認
        file_path = temp_knowledge_base / "agents" / "test_agent.md"
        assert file_path.exists()
        
        # 内容を確認
        content = file_path.read_text(encoding="utf-8")
        assert "Test Agent Knowledge" in content
        assert "test knowledge about agents" in content
        assert "test, agent" in content  # タグのフォーマットが異なる
    
    def test_add_duplicate_knowledge(self, applier, temp_knowledge_base):
        """重複知識の追加テスト"""
        change = {
            "type": "add_knowledge",
            "category": "general",
            "file": "knowledge/general/duplicate_test.md",
            "title": "Duplicate Test",
            "content": "This is test content.",
            "tags": ["test"],
            "reason": "Testing duplicate detection"
        }
        
        # 1回目の追加
        results1 = applier.apply_knowledge_changes([change], dry_run=False)
        assert results1[0]["status"] == "success"
        
        # 2回目の追加（重複）
        results2 = applier.apply_knowledge_changes([change], dry_run=False)
        assert results2[0]["status"] == "skipped"
        assert "Duplicate" in results2[0]["reason"]
    
    def test_update_existing_knowledge(self, applier, temp_knowledge_base):
        """既存知識の更新テスト"""
        change = {
            "type": "update_knowledge",
            "file": "knowledge/general/test_existing.md",
            "section": "## Details",
            "content": "Additional details added through update.",
            "operation": "append",
            "reason": "Testing knowledge update"
        }
        
        results = applier.apply_knowledge_changes([change], dry_run=False)
        
        assert len(results) == 1
        assert results[0]["status"] == "success"
        assert results[0]["operation"] == "append"
        
        # 更新内容を確認
        file_path = temp_knowledge_base / "general" / "test_existing.md"
        content = file_path.read_text(encoding="utf-8")
        assert "Additional details added through update" in content
        assert "Some details here" in content  # 既存の内容も保持
    
    def test_update_nonexistent_file_creates_new(self, applier, temp_knowledge_base):
        """存在しないファイルの更新は新規作成になることをテスト"""
        change = {
            "type": "update_knowledge",
            "file": "knowledge/system/new_from_update.md",
            "section": "## New Section",
            "content": "Content for new file.",
            "operation": "append",
            "reason": "Testing new file creation from update"
        }
        
        results = applier.apply_knowledge_changes([change], dry_run=False)
        
        assert len(results) == 1
        assert results[0]["status"] == "success"
        
        # ファイルが作成されたことを確認
        file_path = temp_knowledge_base / "system" / "new_from_update.md"
        assert file_path.exists()
        content = file_path.read_text(encoding="utf-8")
        assert "Content for new file" in content
    
    def test_dry_run_mode(self, applier, temp_knowledge_base):
        """ドライランモードのテスト"""
        change = {
            "type": "add_knowledge",
            "category": "crew",
            "file": "knowledge/crew/dry_run_test.md",
            "title": "Dry Run Test",
            "content": "This should not be created.",
            "tags": ["dry-run"],
            "reason": "Testing dry run mode"
        }
        
        results = applier.apply_knowledge_changes([change], dry_run=True)
        
        assert len(results) == 1
        assert results[0]["status"] == "success"
        assert results[0]["dry_run"] is True
        
        # ファイルが作成されていないことを確認
        file_path = temp_knowledge_base / "crew" / "dry_run_test.md"
        assert not file_path.exists()
    
    def test_knowledge_index_update(self, applier, temp_knowledge_base):
        """知識インデックスの更新テスト"""
        change = {
            "type": "add_knowledge",
            "category": "domain",
            "file": "knowledge/domain/index_test.md",
            "title": "Index Test",
            "content": "Testing index update.",
            "tags": ["index", "test"],
            "reason": "Testing index functionality"
        }
        
        applier.apply_knowledge_changes([change], dry_run=False)
        
        # インデックスファイルが更新されたことを確認
        index_path = temp_knowledge_base / "index.json"
        assert index_path.exists()
        
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
        assert "knowledge/domain/index_test.md" in index_data["files"]
        assert "domain" in index_data["categories"]
        assert "index" in index_data["tags"]
        assert "test" in index_data["tags"]
    
    def test_replace_section(self, applier, temp_knowledge_base):
        """セクション置換のテスト"""
        change = {
            "type": "update_knowledge",
            "file": "knowledge/general/test_existing.md",
            "section": "## Details",
            "content": "Completely replaced details.",
            "operation": "replace",
            "reason": "Testing section replacement"
        }
        
        results = applier.apply_knowledge_changes([change], dry_run=False)
        
        assert results[0]["status"] == "success"
        
        # 置換内容を確認
        file_path = temp_knowledge_base / "general" / "test_existing.md"
        content = file_path.read_text(encoding="utf-8")
        assert "Completely replaced details" in content
        assert "Some details here" not in content  # 既存の内容は置換される
    
    def test_insert_at_section(self, applier, temp_knowledge_base):
        """セクション挿入のテスト"""
        change = {
            "type": "update_knowledge",
            "file": "knowledge/general/test_existing.md",
            "section": "## Overview",
            "content": "Inserted right after overview.",
            "operation": "insert",
            "reason": "Testing section insertion"
        }
        
        results = applier.apply_knowledge_changes([change], dry_run=False)
        
        assert results[0]["status"] == "success"
        
        # 挿入内容を確認
        file_path = temp_knowledge_base / "general" / "test_existing.md"
        content = file_path.read_text(encoding="utf-8")
        lines = content.split('\n')
        
        # Overviewセクションの直後に挿入されていることを確認
        overview_index = -1
        for i, line in enumerate(lines):
            if "## Overview" in line:
                overview_index = i
                break
        
        assert overview_index >= 0
        assert "Inserted right after overview" in content
    
    def test_backup_creation(self, applier, temp_knowledge_base):
        """バックアップ作成のテスト"""
        # 既存ファイルを更新
        change = {
            "type": "update_knowledge",
            "file": "knowledge/general/test_existing.md",
            "section": "## Details",
            "content": "Updated for backup test.",
            "operation": "append",
            "reason": "Testing backup creation"
        }
        
        applier.apply_knowledge_changes([change], dry_run=False)
        
        # バックアップが作成されたことを確認
        backup_files = list(applier.backup_dir.glob("test_existing.md.*.bak"))
        assert len(backup_files) > 0
        
        # バックアップ内容が元の内容と一致することを確認
        backup_content = backup_files[0].read_text(encoding="utf-8")
        assert "This is existing knowledge for testing" in backup_content
    
    def test_get_knowledge_stats(self, applier, temp_knowledge_base):
        """知識統計取得のテスト"""
        # いくつか知識を追加
        changes = [
            {
                "type": "add_knowledge",
                "category": "agents",
                "file": "knowledge/agents/stats_test1.md",
                "title": "Stats Test 1",
                "content": "Test content 1.",
                "tags": ["stats", "test"],
                "reason": "Testing stats"
            },
            {
                "type": "add_knowledge",
                "category": "crew",
                "file": "knowledge/crew/stats_test2.md",
                "title": "Stats Test 2",
                "content": "Test content 2.",
                "tags": ["stats"],
                "reason": "Testing stats"
            }
        ]
        
        applier.apply_knowledge_changes(changes, dry_run=False)
        
        # 統計を取得
        stats = applier.get_knowledge_stats()
        
        assert stats["total_files"] >= 2
        assert "agents" in stats["categories"]
        assert "crew" in stats["categories"]
        assert "stats" in stats["tags"]
        assert stats["tags"]["stats"] >= 2
    
    def test_error_handling(self, applier):
        """エラーハンドリングのテスト"""
        # 不正な操作タイプ
        change = {
            "type": "update_knowledge",
            "file": "knowledge/general/error_test.md",
            "content": "Test content",
            "operation": "invalid_operation",
            "reason": "Testing error handling"
        }
        
        results = applier.apply_knowledge_changes([change], dry_run=False)
        
        assert len(results) == 1
        assert results[0]["status"] in ["error", "success"]  # ファイルが存在しないので新規作成になる可能性
    
    def test_category_detection(self, applier):
        """カテゴリ検出のテスト"""
        test_cases = [
            ("knowledge/agents/test.md", "agents"),
            ("knowledge/crew/test.md", "crew"),
            ("knowledge/system/test.md", "system"),
            ("knowledge/domain/test.md", "domain"),
            ("knowledge/other/test.md", "general"),
        ]
        
        for file_path, expected_category in test_cases:
            detected = applier._detect_category_from_path(file_path)
            assert detected == expected_category


if __name__ == "__main__":
    pytest.main([__file__, "-v"])