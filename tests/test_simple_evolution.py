#!/usr/bin/env python3
"""シンプルな自己成長機能のテスト"""

import json
from pathlib import Path

# システムパスの設定
import sys
sys.path.append(str(Path(__file__).parent))

from evolution.improvement_parser import ImprovementParser
from evolution.improvement_applier import ImprovementApplier

def test_simple_evolution():
    """直接的な自己成長機能のテスト"""
    print("=== Simple Evolution Test ===")
    
    # テスト用の改善案を作成
    test_changes = [
        {
            "type": "update_agent_parameter",
            "agent": "research_agent",
            "parameter": "max_iter",
            "value": 40,
            "reason": "より詳細な調査のため"
        },
        {
            "type": "add_knowledge",
            "file": "knowledge/evolution_test2.md",
            "content": "## Evolution Test 2\n\nThis is a test knowledge file created by evolution system.",
            "reason": "テスト用の知識追加"
        },
        {
            "type": "create_agent",
            "file": "config/agents/test_agent2.yaml",
            "config": {
                "test_agent2": {
                    "role": "Test Agent 2",
                    "goal": "Test the evolution system",
                    "backstory": "Created by evolution test",
                    "max_iter": 5,
                    "tools": []
                }
            },
            "reason": "テスト用エージェント作成"
        }
    ]
    
    # 改善の適用
    print("\n改善の適用...")
    parser = ImprovementParser()
    applier = ImprovementApplier()
    
    # 改善を正しい形式に変換
    parsed_changes = []
    for change in test_changes:
        if change["type"] == "update_agent_parameter":
            parsed_changes.append((
                f"config/agents/{change['agent']}.yaml",
                "update_field",
                {
                    "field": change["parameter"],
                    "value": change["value"]
                }
            ))
        elif change["type"] == "add_knowledge":
            parsed_changes.append((
                change["file"],
                "add",
                {
                    "content": change["content"]
                }
            ))
        elif change["type"] == "create_agent":
            parsed_changes.append((
                change["file"],
                "add",
                {
                    "content": change["config"]
                }
            ))
    
    print(f"解析された変更: {len(parsed_changes)}件")
    results = applier.apply_changes(parsed_changes, dry_run=False)
    
    print(f"\n適用結果:")
    print(f"  - 成功: {results['applied']}件")
    print(f"  - 失敗: {results['failed']}件")
    print(f"  - スキップ: {results['skipped']}件")
    
    # 適用結果の確認
    print("\n適用結果の確認:")
    
    # 1. エージェント設定の確認
    agent_file = Path("config/agents/research_agent.yaml")
    if agent_file.exists():
        with open(agent_file, 'r') as f:
            content = f.read()
            if "max_iter: 40" in content:
                print("✓ research_agent.max_iter が 40 に更新されました")
            else:
                print("✗ research_agent.max_iter の更新に失敗")
    
    # 2. 知識ファイルの確認
    knowledge_file = Path("knowledge/evolution_test2.md")
    if knowledge_file.exists():
        print(f"✓ {knowledge_file} が作成されました")
    else:
        print(f"✗ {knowledge_file} の作成に失敗")
    
    # 3. 新規エージェントの確認
    new_agent_file = Path("config/agents/test_agent2.yaml")
    if new_agent_file.exists():
        print(f"✓ {new_agent_file} が作成されました")
    else:
        print(f"✗ {new_agent_file} の作成に失敗")
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_simple_evolution()