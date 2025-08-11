"""
Evolution統合テスト
実際のevolution crewとファイル作成処理の統合テスト
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from evolution.improvement_parser import ImprovementParser
from evolution.improvement_applier import ImprovementApplier


class TestEvolutionIntegration:
    """Evolution統合テストクラス"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def parser(self):
        """ImprovementParserのインスタンスを作成"""
        return ImprovementParser()
    
    @pytest.fixture
    def applier(self, temp_dir):
        """ImprovementApplierのインスタンスを作成"""
        return ImprovementApplier(base_path=temp_dir)
    
    def test_real_evolution_json_processing(self, parser, applier, temp_dir):
        """実際のevolution crewが出力するJSONの処理をテスト"""
        # 実際のログから取得したJSONスタイル
        evolution_result = '''
        {
            "type": "add_knowledge",
            "file": "knowledge/optimization_best_practices.md",
            "content": "**Optimization Tactics:**\\n- Database query performance improvements with caching and indexing techniques.\\n- Resource scaling strategies using dynamic allocation.\\n**NLP Integration:**\\n- Using BERT or GPT for improved accuracy in nuanced query handling.\\n**Error Mitigation:**\\n- Implementation of fallback patterns for handling user edge cases gracefully.",
            "reason": "To provide clear guidelines for implementing recommended improvement strategies within the OKAMI system."
        }
        '''
        
        # 解析をテスト
        improvements = parser.parse_improvements(evolution_result)
        assert len(improvements["knowledge"]) == 1
        
        # アクション可能な変更に変換
        actionable_changes = parser.extract_actionable_changes(improvements)
        assert len(actionable_changes) == 1
        
        file_path, action, changes = actionable_changes[0]
        assert file_path == "knowledge/optimization_best_practices.md"
        assert action == "add"
        assert "Optimization Tactics" in changes["content"]
        
        # 実際にファイルを作成
        results = applier.apply_changes(actionable_changes, dry_run=False)
        
        # 結果を確認
        assert len(results["applied"]) == 1
        assert len(results["failed"]) == 0
        assert len(results["skipped"]) == 0
        
        # ファイルが作成されたことを確認
        created_file = Path(temp_dir) / "knowledge" / "optimization_best_practices.md"
        assert created_file.exists()
        
        # ファイル内容を確認
        content = created_file.read_text(encoding="utf-8")
        assert "Optimization Tactics" in content
        assert "Database query performance improvements" in content
        assert "OKAMI Evolution System" in content  # タイムスタンプメッセージ
    
    def test_file_creation_with_directory_creation(self, parser, applier, temp_dir):
        """ディレクトリが存在しない場合のファイル作成をテスト"""
        evolution_result = '''
        {
            "type": "add_knowledge",
            "file": "knowledge/new_category/advanced_techniques.md",
            "content": "# Advanced AI Techniques\\n\\nThis document contains advanced techniques for AI optimization.",
            "reason": "To provide specialized knowledge in a new category."
        }
        '''
        
        improvements = parser.parse_improvements(evolution_result)
        actionable_changes = parser.extract_actionable_changes(improvements)
        
        # ファイルを作成（ディレクトリも自動作成される）
        results = applier.apply_changes(actionable_changes, dry_run=False)
        
        assert len(results["applied"]) == 1
        
        # ディレクトリとファイルが作成されたことを確認
        created_file = Path(temp_dir) / "knowledge" / "new_category" / "advanced_techniques.md"
        assert created_file.exists()
        assert created_file.parent.exists()
        
        content = created_file.read_text(encoding="utf-8")
        assert "Advanced AI Techniques" in content
        assert "advanced techniques for AI" in content
    
    def test_existing_file_update(self, parser, applier, temp_dir):
        """既存ファイルへの追記をテスト"""
        # 既存ファイルを作成
        existing_file = Path(temp_dir) / "knowledge" / "existing.md"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_text("# Existing Content\n\nThis is existing content.", encoding="utf-8")
        
        evolution_result = '''
        {
            "type": "add_knowledge",
            "file": "knowledge/existing.md",
            "content": "## New Section\\n\\nThis is additional content added by evolution.",
            "reason": "To enhance existing knowledge."
        }
        '''
        
        improvements = parser.parse_improvements(evolution_result)
        actionable_changes = parser.extract_actionable_changes(improvements)
        
        # バックアップディレクトリを作成
        (Path(temp_dir) / "evolution" / "backups").mkdir(parents=True, exist_ok=True)
        
        results = applier.apply_changes(actionable_changes, dry_run=False)
        
        assert len(results["applied"]) == 1
        
        # ファイル内容を確認（既存内容＋新規内容）
        content = existing_file.read_text(encoding="utf-8")
        assert "Existing Content" in content  # 既存内容が保持されている
        assert "New Section" in content      # 新規内容が追加されている
        assert "additional content added by evolution" in content
        
        # バックアップが作成されたことを確認
        backup_files = list((Path(temp_dir) / "evolution" / "backups").glob("existing.md.*.bak"))
        assert len(backup_files) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])