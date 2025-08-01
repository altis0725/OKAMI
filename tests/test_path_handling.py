#!/usr/bin/env python3
"""
CrewAI TextFileKnowledgeSourceのパス処理テスト
パス重複問題の調査と検証
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.utilities.constants import KNOWLEDGE_DIRECTORY
from crewai.utilities.paths import db_storage_path
from core.knowledge_manager import KnowledgeManager

def test_path_handling():
    """パス処理の動作を詳しくテスト"""
    print("=== CrewAI TextFileKnowledgeSource パス処理テスト ===\n")
    
    # 1. KNOWLEDGE_DIRECTORYの確認
    print(f"1. KNOWLEDGE_DIRECTORY: {KNOWLEDGE_DIRECTORY}")
    print(f"   現在の作業ディレクトリ: {os.getcwd()}")
    print(f"   プロジェクトルート: {project_root}")
    print(f"   knowledgeディレクトリ: {project_root / 'knowledge'}")
    print()
    
    # 2. db_storage_pathの確認
    storage_path = db_storage_path()
    print(f"2. CrewAI storage path: {storage_path}")
    knowledge_storage_path = os.path.join(storage_path, "knowledge")
    print(f"   Knowledge storage path: {knowledge_storage_path}")
    print()
    
    # 3. テスト用一時ディレクトリの作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_knowledge_dir = Path(temp_dir) / "knowledge"
        temp_knowledge_dir.mkdir()
        
        # テストファイルを作成
        test_file = temp_knowledge_dir / "test_content.md"
        test_content = "# テストファイル\n\nこれはテスト用のコンテンツです。"
        test_file.write_text(test_content, encoding='utf-8')
        
        print(f"3. テスト環境:")
        print(f"   一時ディレクトリ: {temp_dir}")
        print(f"   knowledgeディレクトリ: {temp_knowledge_dir}")
        print(f"   テストファイル: {test_file}")
        print(f"   ファイルの存在確認: {test_file.exists()}")
        print()
        
        # 4. 異なるパス指定方法をテスト
        test_cases = [
            ("相対パス (filename only)", "test_content.md"),
            ("相対パス (knowledge/filename)", "knowledge/test_content.md"),
            ("絶対パス", str(test_file)),
        ]
        
        # 作業ディレクトリを一時ディレクトリに変更
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            for case_name, file_path in test_cases:
                print(f"4. テストケース: {case_name}")
                print(f"   入力パス: {file_path}")
                
                try:
                    # TextFileKnowledgeSourceを作成
                    source = TextFileKnowledgeSource(file_paths=[file_path])
                    print(f"   ✓ TextFileKnowledgeSource作成成功")
                    print(f"   file_paths: {source.file_paths}")
                    
                    # validate_contentを呼び出してパス解決をテスト
                    try:
                        content_dict = source.validate_content()
                        print(f"   ✓ validate_content成功")
                        print(f"   解決されたパス: {list(content_dict.keys())}")
                        for path, content in content_dict.items():
                            print(f"   コンテンツ: {content[:50]}...")
                    except Exception as e:
                        print(f"   ✗ validate_content失敗: {e}")
                    
                except Exception as e:
                    print(f"   ✗ TextFileKnowledgeSource作成失敗: {e}")
                
                print()
        
        finally:
            os.chdir(original_cwd)
    
    # 5. OKAMIのKnowledgeManagerでのテスト
    print("5. OKAMIのKnowledgeManagerでのテスト:")
    
    # 実際のknowledgeディレクトリを使用
    knowledge_dir = project_root / "knowledge"
    if knowledge_dir.exists():
        print(f"   Knowledge directory: {knowledge_dir}")
        
        # テストファイルを探す
        test_files = list(knowledge_dir.glob("**/*.md"))[:3]  # 最初の3つのファイル
        
        for test_file in test_files:
            relative_to_knowledge = test_file.relative_to(knowledge_dir)
            relative_to_project = test_file.relative_to(project_root)
            
            print(f"\n   テストファイル: {test_file.name}")
            print(f"   絶対パス: {test_file}")
            print(f"   knowledgeからの相対パス: {relative_to_knowledge}")
            print(f"   プロジェクトからの相対パス: {relative_to_project}")
            
            try:
                # KnowledgeManagerを使ってソースを作成
                km = KnowledgeManager(knowledge_dir=str(knowledge_dir))
                source = km.create_knowledge_source(str(test_file))
                print(f"   ✓ KnowledgeManager.create_knowledge_source成功")
                print(f"   file_paths: {source.file_paths}")
            except Exception as e:
                print(f"   ✗ KnowledgeManager.create_knowledge_source失敗: {e}")
    
    else:
        print(f"   ✗ Knowledge directory not found: {knowledge_dir}")

def test_duplicate_path_issue():
    """パス重複問題の再現テスト"""
    print("\n=== パス重複問題の再現テスト ===\n")
    
    knowledge_dir = project_root / "knowledge"
    
    # 問題が発生するケースをシミュレート
    test_cases = [
        # 正しいパス指定
        ("crew/best_practices.md", "正しい相対パス"),
        # 問題を引き起こす可能性のあるパス指定
        ("knowledge/crew/best_practices.md", "knowledge/を含む相対パス"),
        (str(knowledge_dir / "crew" / "best_practices.md"), "絶対パス"),
    ]
    
    km = KnowledgeManager(knowledge_dir=str(knowledge_dir))
    
    for file_path, description in test_cases:
        print(f"テストケース: {description}")
        print(f"入力パス: {file_path}")
        
        try:
            source = km.create_knowledge_source(file_path)
            print(f"処理後のfile_paths: {source.file_paths}")
            
            # validate_contentで実際のファイル検索をテスト
            try:
                if hasattr(source, 'validate_content'):
                    content_dict = source.validate_content()
                    print(f"✓ ファイル読み込み成功: {len(content_dict)} files")
                    for path in content_dict.keys():
                        print(f"  実際に読み込まれたパス: {path}")
                else:
                    print("validate_content メソッドが存在しません")
            except Exception as e:
                print(f"✗ ファイル読み込み失敗: {e}")
        
        except Exception as e:
            print(f"✗ ソース作成失敗: {e}")
        
        print()

if __name__ == "__main__":
    test_path_handling()
    test_duplicate_path_issue()