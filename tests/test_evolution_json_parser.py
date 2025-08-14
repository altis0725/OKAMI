"""
Evolution System JSON Parser Test
JSONパース処理の修正をテスト
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evolution.improvement_parser import ImprovementParser


def test_nested_json_extraction():
    """ネストされたJSONの抽出をテスト"""
    parser = ImprovementParser()
    
    # Evolution Crewが出力する形式のサンプル
    evolution_result = """
    Analysis complete. Here are the improvements:
    
    {
      "changes": [
        {
          "type": "update_agent_parameter",
          "agent": "OKAMI_system",
          "parameter": "training_modules",
          "value": "advanced learning for complex non-standard scenarios",
          "reason": "To enhance agent adaptability and reduce manual intervention needs."
        },
        {
          "type": "add_knowledge",
          "file": "knowledge/system_scaling.md",
          "content": "Guidelines and methodologies on dynamic resource scaling and load-balancing strategies for enhanced scalability.",
          "reason": "To provide system documentation supporting real-time upgrades for peak-hour resource demand."
        }
      ]
    }
    
    Additional notes...
    """
    
    # JSON actionsを抽出
    improvements = parser._extract_json_actions(evolution_result)
    
    print("Extracted improvements:")
    print(json.dumps(improvements, indent=2, ensure_ascii=False))
    
    # アサーション
    assert improvements is not None, "Should extract improvements"
    assert len(improvements["agents"]) == 1, "Should extract 1 agent improvement"
    assert len(improvements["knowledge"]) == 1, "Should extract 1 knowledge improvement"
    
    # エージェント改善の確認
    agent_imp = improvements["agents"][0]
    assert agent_imp["field"] == "training_modules"
    assert agent_imp["value"] == "advanced learning for complex non-standard scenarios"
    
    # 知識改善の確認
    knowledge_imp = improvements["knowledge"][0]
    assert knowledge_imp["action"] == "add"
    assert knowledge_imp["file"] == "knowledge/system_scaling.md"
    assert "Guidelines and methodologies" in knowledge_imp["content"]
    
    print("✅ Test passed: Nested JSON extraction works correctly")


def test_balanced_bracket_extraction():
    """バランスの取れた括弧の抽出をテスト"""
    parser = ImprovementParser()
    
    # 複雑なネストを含むテキスト
    text = """
    {
      "type": "add_knowledge",
      "content": "This has {nested} brackets",
      "data": {"inner": {"deep": "value"}}
    }
    Some text
    {"simple": "object"}
    """
    
    json_objects = parser._extract_balanced_json_objects(text)
    
    print(f"Found {len(json_objects)} JSON objects")
    
    assert len(json_objects) == 2, "Should find 2 JSON objects"
    
    # 最初のオブジェクトを解析
    obj1 = json.loads(json_objects[0])
    assert obj1["type"] == "add_knowledge"
    assert "{nested}" in obj1["content"]
    assert obj1["data"]["inner"]["deep"] == "value"
    
    # 2番目のオブジェクトを解析
    obj2 = json.loads(json_objects[1])
    assert obj2["simple"] == "object"
    
    print("✅ Test passed: Balanced bracket extraction works correctly")


def test_changes_array_parsing():
    """changes配列の解析をテスト"""
    parser = ImprovementParser()
    
    # CrewAIが返す可能性のある形式
    evolution_result = '''
    The analysis is complete. Here are my recommendations:
    
    "changes": [
      {
        "type": "add_knowledge",
        "file": "knowledge/best_practices.md",
        "content": "Best practices for system optimization",
        "reason": "To improve system performance"
      },
      {
        "type": "update_agent_parameter",
        "agent": "research_agent",
        "parameter": "max_iter",
        "value": 30,
        "reason": "To allow more iterations for complex tasks"
      }
    ]
    
    These changes will improve the system.
    '''
    
    improvements = parser._extract_json_actions(evolution_result)
    
    print("Extracted from changes array:")
    print(json.dumps(improvements, indent=2, ensure_ascii=False))
    
    assert improvements is not None, "Should extract improvements"
    assert len(improvements["knowledge"]) == 1, "Should extract knowledge improvement"
    assert len(improvements["agents"]) == 1, "Should extract agent improvement"
    
    print("✅ Test passed: Changes array parsing works correctly")


def test_actionable_changes_conversion():
    """改善を実行可能な変更に変換するテスト"""
    parser = ImprovementParser()
    
    improvements = {
        "knowledge": [
            {
                "action": "add",
                "file": "knowledge/test.md",
                "content": "Test content",
                "reason": "Test reason"
            }
        ],
        "agents": [
            {
                "agent": "research_agent",
                "field": "goal",
                "value": "New goal",
                "reason": "Update goal"
            }
        ],
        "tasks": [],
        "config": []
    }
    
    actions = parser.extract_actionable_changes(improvements)
    
    print(f"Generated {len(actions)} actionable changes")
    
    assert len(actions) == 2, "Should generate 2 actions"
    
    # 知識追加アクション
    knowledge_action = actions[0]
    assert knowledge_action[0] == "knowledge/test.md"
    assert knowledge_action[1] == "add"
    assert knowledge_action[2]["content"] == "Test content"
    
    # エージェント更新アクション
    agent_action = actions[1]
    assert agent_action[0] == "config/agents/research_agent.yaml"
    assert agent_action[1] == "update_field"
    assert agent_action[2]["field"] == "goal"
    assert agent_action[2]["value"] == "New goal"
    
    print("✅ Test passed: Actionable changes conversion works correctly")


def test_full_parsing_pipeline():
    """完全なパーシングパイプラインをテスト"""
    parser = ImprovementParser()
    
    # 実際のEvolution Crewの出力に近い形式
    evolution_result = """
    Based on my analysis of the OKAMI system, I've identified several improvements:
    
    ## Proposed Changes
    
    {
      "changes": [
        {
          "type": "add_knowledge",
          "file": "knowledge/troubleshooting.md",
          "content": "Common troubleshooting steps:\\n1. Check Docker status\\n2. Verify API keys\\n3. Review logs",
          "reason": "To help users debug common issues"
        },
        {
          "type": "update_agent_parameter",
          "agent": "analysis_agent",
          "parameter": "tools",
          "value": ["search_tool", "calculator_tool"],
          "reason": "To enhance analysis capabilities"
        }
      ]
    }
    
    These improvements will enhance system reliability and performance.
    """
    
    # 完全なパーシングパイプラインを実行
    improvements = parser.parse_improvements(evolution_result)
    actions = parser.extract_actionable_changes(improvements)
    
    print(f"Full pipeline: {len(actions)} actions generated")
    
    for i, (file_path, action, changes) in enumerate(actions):
        print(f"  Action {i+1}: {action} on {file_path}")
        print(f"    Changes: {changes}")
    
    assert len(actions) > 0, "Should generate at least one action"
    
    print("✅ Test passed: Full parsing pipeline works correctly")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Evolution System JSON Parser Fix")
    print("=" * 60)
    
    try:
        test_balanced_bracket_extraction()
        print()
        test_nested_json_extraction()
        print()
        test_changes_array_parsing()
        print()
        test_actionable_changes_conversion()
        print()
        test_full_parsing_pipeline()
        print()
        print("=" * 60)
        print("✅ All tests passed successfully!")
        print("=" * 60)
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()