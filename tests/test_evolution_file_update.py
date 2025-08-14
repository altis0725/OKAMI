#!/usr/bin/env python3
"""
Evolution System File Update のテスト
フェーズ2.5.5の修正が正しく動作することを確認
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evolution.improvement_applier import ImprovementApplier


def test_basic_file_creation():
    """基本的なファイル作成のテスト"""
    print("Testing basic file creation...")
    
    applier = ImprovementApplier()
    test_file = "knowledge/test_knowledge_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".md"
    
    changes = [
        (test_file, "add", {"content": "# Test Knowledge\n\nThis is test content for the evolution system."})
    ]
    
    result = applier.apply_changes(changes, dry_run=False)
    
    if result["applied"]:
        print(f"✓ File created successfully: {result['applied'][0]['file']}")
        print(f"  Content added: {result['applied'][0]['content_added']} characters")
        
        # ファイルが実際に存在するか確認
        file_path = Path(result['applied'][0]['file'])
        if file_path.exists():
            print(f"✓ File exists on disk: {file_path}")
            # テストファイルを削除
            file_path.unlink()
            print(f"  Test file cleaned up")
        else:
            print(f"✗ File does not exist on disk: {file_path}")
            return False
    else:
        print(f"✗ Failed to create file")
        if result["failed"]:
            print(f"  Error: {result['failed'][0].get('error', 'Unknown error')}")
        if result["skipped"]:
            print(f"  Skipped: {result['skipped'][0].get('reason', 'Unknown reason')}")
        return False
    
    return True


def test_evolution_history_redirect():
    """Evolution履歴のリダイレクトテスト"""
    print("\nTesting evolution history redirect...")
    
    applier = ImprovementApplier()
    
    changes = [
        ("knowledge/general.md", "add", {"content": "Evolution Update - This should go to evolution_history.md"})
    ]
    
    result = applier.apply_changes(changes, dry_run=False)
    
    if result["applied"]:
        applied_file = result['applied'][0]['file']
        print(f"✓ Content redirected to: {applied_file}")
        
        if "evolution_history.md" in applied_file:
            print(f"✓ Correctly redirected to evolution_history.md")
            return True
        else:
            print(f"✗ Not redirected to evolution_history.md")
            return False
    else:
        print(f"✗ Failed to apply changes")
        return False


def test_invalid_content_detection():
    """不正なコンテンツ（ファイルパス）の検出テスト"""
    print("\nTesting invalid content detection...")
    
    applier = ImprovementApplier()
    
    changes = [
        ("knowledge/test.md", "add", {"content": '"file": "knowledge/wrong_content.md"'})
    ]
    
    result = applier.apply_changes(changes, dry_run=False)
    
    if result["skipped"]:
        reason = result['skipped'][0].get('reason', '')
        print(f"✓ Invalid content detected and skipped")
        print(f"  Reason: {reason}")
        
        if "file path" in reason.lower():
            print(f"✓ Correctly identified as file path")
            return True
        else:
            print(f"✗ Skipped for wrong reason")
            return False
    else:
        print(f"✗ Invalid content not detected")
        return False


def test_directory_creation():
    """ディレクトリが存在しない場合の自動作成テスト"""
    print("\nTesting automatic directory creation...")
    
    applier = ImprovementApplier()
    test_dir = "knowledge/test_subdir_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    test_file = f"{test_dir}/test_file.md"
    
    changes = [
        (test_file, "add", {"content": "# Test in Subdirectory\n\nThis tests directory creation."})
    ]
    
    result = applier.apply_changes(changes, dry_run=False)
    
    if result["applied"]:
        print(f"✓ File created with directory: {result['applied'][0]['file']}")
        
        # ファイルとディレクトリが存在するか確認
        file_path = Path(result['applied'][0]['file'])
        if file_path.exists() and file_path.parent.exists():
            print(f"✓ Directory and file exist on disk")
            # テストファイルとディレクトリを削除
            file_path.unlink()
            file_path.parent.rmdir()
            print(f"  Test directory cleaned up")
            return True
        else:
            print(f"✗ Directory or file does not exist")
            return False
    else:
        print(f"✗ Failed to create file with directory")
        return False


def main():
    """メインテスト実行"""
    print("=" * 60)
    print("Evolution System File Update Test Suite")
    print("Phase 2.5.5 Fix Verification")
    print("=" * 60)
    
    tests = [
        ("Basic File Creation", test_basic_file_creation),
        ("Evolution History Redirect", test_evolution_history_redirect),
        ("Invalid Content Detection", test_invalid_content_detection),
        ("Directory Auto-Creation", test_directory_creation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' raised an exception: {e}")
            results.append((test_name, False))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Evolution System file update is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())