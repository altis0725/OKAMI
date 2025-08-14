#!/usr/bin/env python
"""知識管理統合テストスクリプト"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath('.'))

from evolution.knowledge_applier import KnowledgeApplier
from evolution.improvement_applier import ImprovementApplier


def test_knowledge_applier():
    """KnowledgeApplierの基本的な動作確認"""
    print("=" * 60)
    print("KnowledgeApplier 動作テスト")
    print("=" * 60)
    
    # テスト用のKnowledgeApplierを作成
    applier = KnowledgeApplier(Path("knowledge"))
    
    # 1. 新規知識の追加テスト
    print("\n1. 新規知識の追加テスト")
    test_change = {
        "type": "add_knowledge",
        "category": "system",
        "file": "knowledge/system/test_integration.md",
        "title": "Integration Test Knowledge",
        "content": "This is a test knowledge created by integration test.",
        "tags": ["test", "integration", "system"],
        "reason": "Testing knowledge management system"
    }
    
    results = applier.apply_knowledge_changes([test_change], dry_run=True)
    print(f"ドライラン結果: {json.dumps(results, indent=2, ensure_ascii=False)}")
    
    # 実際に適用
    results = applier.apply_knowledge_changes([test_change], dry_run=False)
    print(f"実行結果: {json.dumps(results, indent=2, ensure_ascii=False)}")
    
    # 2. 既存知識の更新テスト
    print("\n2. 既存知識の更新テスト")
    update_change = {
        "type": "update_knowledge",
        "file": "knowledge/system/test_integration.md",
        "section": "## Additional Information",
        "content": "This section was added by update operation.",
        "operation": "append",
        "reason": "Testing update functionality"
    }
    
    results = applier.apply_knowledge_changes([update_change], dry_run=False)
    print(f"更新結果: {json.dumps(results, indent=2, ensure_ascii=False)}")
    
    # 3. 知識統計の取得
    print("\n3. 知識統計の取得")
    stats = applier.get_knowledge_stats()
    print(f"統計情報: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    return True


def test_improvement_applier_integration():
    """ImprovementApplierとKnowledgeApplierの統合テスト"""
    print("\n" + "=" * 60)
    print("ImprovementApplier 統合テスト")
    print("=" * 60)
    
    # ImprovementApplierを作成
    applier = ImprovementApplier(".")
    
    # 知識関連の変更をテスト
    print("\n知識ファイルへの変更テスト")
    changes = [
        (
            "knowledge/crew/integration_test.md",
            "add",
            {
                "content": "# Crew Integration Test\n\nThis knowledge was added through ImprovementApplier.",
                "title": "Crew Integration Test",
                "tags": ["crew", "integration"],
                "reason": "Testing ImprovementApplier integration"
            }
        )
    ]
    
    results = applier.apply_changes(changes, dry_run=False)
    print(f"統合結果: {json.dumps(results, indent=2, ensure_ascii=False)}")
    
    return True


def main():
    """メインテスト実行"""
    print("OKAMI Evolution System - 知識管理統合テスト")
    print("実行時刻:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    try:
        # KnowledgeApplierのテスト
        if test_knowledge_applier():
            print("\n✅ KnowledgeApplier テスト成功")
        
        # 統合テスト
        if test_improvement_applier_integration():
            print("\n✅ ImprovementApplier 統合テスト成功")
        
        print("\n" + "=" * 60)
        print("すべてのテストが成功しました！")
        print("=" * 60)
        
        # テストファイルのクリーンアップ（オプション）
        print("\nテストファイルのクリーンアップ...")
        test_files = [
            "knowledge/system/test_integration.md",
            "knowledge/crew/integration_test.md"
        ]
        
        for file_path in test_files:
            if Path(file_path).exists():
                print(f"削除: {file_path}")
                Path(file_path).unlink()
        
        print("クリーンアップ完了")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())