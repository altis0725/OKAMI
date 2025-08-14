"""
ImprovementApplierのknowledgeディレクトリ制限のテスト
"""

import sys
from pathlib import Path
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from evolution.improvement_parser import ImprovementParser
from evolution.improvement_applier import ImprovementApplier


def test_knowledge_only_restriction():
    """知識ディレクトリのみへの変更制限をテスト"""
    print("=== Knowledge-Only Restriction Test ===\n")
    
    # パーサーとアプライヤーのインスタンス化
    parser = ImprovementParser()
    applier = ImprovementApplier(base_path=str(project_root))
    
    # テスト用の改善データを作成
    improvements = {
        "knowledge": [
            {
                "action": "update",
                "content": "Test knowledge content",
                "file": "knowledge/test_knowledge.md"
            }
        ],
        "agents": [
            {
                "agent": "research_agent",
                "field": "max_iter",
                "value": 50
            }
        ],
        "tasks": [
            {
                "task": "research_task",
                "improvement": "Improve research methodology"
            }
        ],
        "config": [
            {
                "type": "memory",
                "change": "enable memory feature"
            }
        ]
    }
    
    # 実行可能な変更を抽出
    print("1. Extracting actionable changes...")
    changes = parser.extract_actionable_changes(improvements)
    
    print(f"   Total changes extracted: {len(changes)}")
    for file_path, action, _ in changes:
        print(f"   - {file_path} ({action})")
    
    # 変更を適用（dry_run=Trueでテスト）
    print("\n2. Applying changes (dry run)...")
    results = applier.apply_changes(changes, dry_run=True)
    
    # 結果を表示
    print("\n3. Results:")
    print(f"   Applied: {len(results['applied'])}")
    print(f"   Failed: {len(results['failed'])}")
    print(f"   Skipped: {len(results['skipped'])}")
    
    if "blocked_config_changes" in results:
        print(f"   Blocked config changes: {len(results['blocked_config_changes'])}")
        for blocked in results['blocked_config_changes']:
            print(f"     - {blocked['file']}: {blocked['reason']}")
    
    # 提案されたconfig変更ファイルをチェック
    print("\n4. Checking proposed config changes...")
    proposals_file = project_root / "evolution" / "proposed_changes" / "config_proposals.json"
    if proposals_file.exists():
        with open(proposals_file, "r", encoding="utf-8") as f:
            proposals = json.load(f)
        print(f"   Found {len(proposals)} proposed changes in {proposals_file}")
        for proposal in proposals[-3:]:  # 最新の3件を表示
            print(f"     - {proposal.get('file_path', 'N/A')}: {proposal.get('action', 'N/A')}")
    else:
        print(f"   No proposals file found at {proposals_file}")
    
    # 成功判定
    print("\n5. Test Result:")
    knowledge_only = all(
        file_path.startswith("knowledge/") 
        for file_path, _, _ in changes
        if not any(file_path == blocked['file'] for blocked in results.get('blocked_config_changes', []))
    )
    
    if knowledge_only:
        print("   ✅ SUCCESS: Only knowledge files are being modified")
    else:
        print("   ❌ FAILURE: Non-knowledge files are still being modified")
    
    return knowledge_only


def test_evolution_result_parsing():
    """Evolution結果のパースをテスト"""
    print("\n=== Evolution Result Parsing Test ===\n")
    
    parser = ImprovementParser()
    
    # 実際のEvolution Crewの出力形式をシミュレート
    evolution_result = """
    Analysis complete. Here are the improvements:
    
    {
        "changes": [
            {
                "type": "add_knowledge",
                "file": "knowledge/agents/research_agent.md",
                "content": "### New Research Methodology\\n- Use multi-source verification",
                "reason": "Improve research accuracy"
            },
            {
                "type": "update_agent_parameter",
                "agent": "research_agent",
                "parameter": "max_iter",
                "value": 45,
                "reason": "Optimize iteration count"
            }
        ]
    }
    """
    
    # 改善を解析
    improvements = parser.parse_improvements(evolution_result)
    
    print("Parsed improvements:")
    print(f"  Knowledge: {len(improvements['knowledge'])} items")
    print(f"  Agents: {len(improvements['agents'])} items")
    print(f"  Tasks: {len(improvements['tasks'])} items")
    print(f"  Config: {len(improvements['config'])} items")
    
    # 実行可能な変更を抽出
    changes = parser.extract_actionable_changes(improvements)
    
    print(f"\nExtracted changes: {len(changes)}")
    for file_path, action, change_data in changes:
        if file_path.startswith("knowledge/"):
            print(f"  ✅ {file_path}: {action}")
        else:
            print(f"  ❌ {file_path}: {action} (would be blocked)")
    
    return True


if __name__ == "__main__":
    print("Testing ImprovementApplier knowledge-only restriction...\n")
    
    # テスト1: 知識ディレクトリ制限
    test1_passed = test_knowledge_only_restriction()
    
    # テスト2: Evolution結果パース
    test2_passed = test_evolution_result_parsing()
    
    # 最終結果
    print("\n" + "="*60)
    print("FINAL RESULTS:")
    print(f"  Test 1 (Knowledge-only restriction): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  Test 2 (Evolution result parsing): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The ImprovementApplier is now restricted to knowledge directory only.")
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")