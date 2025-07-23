#!/usr/bin/env python3
"""自己成長機能の実際のテスト"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

# システムパスの設定
import sys
sys.path.append(str(Path(__file__).parent))

from core.evolution_tracker import EvolutionTracker
from crews.crew_factory import CrewFactory
from evolution.improvement_parser import ImprovementParser
from evolution.improvement_applier import ImprovementApplier
from utils.config import get_config

def test_evolution_cycle():
    """Evolution Crewを使った自己成長サイクルのテスト"""
    print("=== Evolution Crew Test ===")
    
    # 1. まず通常のタスクを実行
    print("\n1. 通常タスクの実行...")
    crew_factory = CrewFactory()
    
    # シンプルなタスクを実行
    test_task = {
        "task": "調査タスク: CrewAIの最新機能について調査してください",
        "crew_name": "simple_crew"
    }
    
    try:
        # CrewFactoryから crew を取得
        crew = crew_factory.get_crew(test_task["crew_name"])
        if not crew:
            raise ValueError(f"Crew '{test_task['crew_name']}' not found")
        
        # タスクを実行
        result = crew.kickoff(inputs={"task": test_task["task"]})
        print(f"タスク結果: {str(result)[:200]}...")  # 最初の200文字を表示
    except Exception as e:
        print(f"タスクエラー: {e}")
        result = f"エラー: {str(e)}"
    
    # 2. Evolution Crewを実行して改善案を生成
    print("\n2. Evolution Crewの実行...")
    evolution_task = {
        "task": f"""前回のタスク実行結果を分析し、改善案を提案してください。

前回のタスク: {test_task['task']}
実行結果: {str(result)[:500]}

分析して以下の形式で改善案を提案してください：
```json
{{
    "changes": [
        {{
            "type": "update_agent_parameter",
            "agent": "research_agent",
            "parameter": "max_iter",
            "value": 35,
            "reason": "より詳細な調査のため"
        }},
        {{
            "type": "add_knowledge",
            "file": "knowledge/crew/simple_crew_lessons.md",
            "content": "## シンプルクルーの学習結果\\n\\n- 調査タスクでは複数のソースを確認することが重要\\n- 結果の要約は簡潔に行う",
            "reason": "今回の実行から得られた知見"
        }}
    ]
}}
```
""",
        "crew_name": "evolution_crew"
    }
    
    try:
        # Evolution Crewを取得して実行
        evolution_crew = crew_factory.get_crew(evolution_task["crew_name"])
        if not evolution_crew:
            raise ValueError(f"Crew '{evolution_task['crew_name']}' not found")
        
        evolution_result = evolution_crew.kickoff(inputs={"task": evolution_task["task"]})
        evolution_result = str(evolution_result)  # 文字列に変換
        print(f"\nEvolution結果: {evolution_result[:500]}...")
        
        # 3. 改善案の解析と適用
        print("\n3. 改善案の解析と適用...")
        parser = ImprovementParser()
        # JSONコードブロックを抽出
        import re
        json_match = re.search(r'```json\s*({.*?})\s*```', evolution_result, re.DOTALL)
        
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                changes = json_data.get('changes', [])
            except json.JSONDecodeError:
                print("JSON解析エラー、テキストベースで解析を試みます")
                improvements = parser.parse_improvements(evolution_result)
                # 改善を変更リストに変換
                changes = []
                for category, items in improvements.items():
                    changes.extend(items)
        else:
            print("JSONブロックが見つかりません、テキストベースで解析を試みます")
            improvements = parser.parse_improvements(evolution_result)
            changes = []
            for category, items in improvements.items():
                changes.extend(items)
        print(f"解析された変更: {len(changes)}件")
        
        applier = ImprovementApplier()
        results = applier.apply_changes(changes, dry_run=False)
        
        print(f"\n適用結果:")
        print(f"  - 成功: {results['applied']}件")
        print(f"  - 失敗: {results['failed']}件")
        print(f"  - スキップ: {results['skipped']}件")
        
        # 4. 進化の記録
        print("\n4. 進化の記録...")
        tracker = EvolutionTracker()
        evolution_entry = {
            "timestamp": datetime.now().isoformat(),
            "task": test_task["task"],
            "analysis": evolution_result[:500],
            "changes_applied": len(changes),
            "success": results['applied'] > 0
        }
        tracker.record_evolution(evolution_entry)
        
        # 最近の進化履歴を表示
        recent = tracker.get_recent_evolutions(limit=3)
        print(f"\n最近の進化履歴: {len(recent)}件")
        
    except Exception as e:
        print(f"Evolution Crewエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_evolution_cycle()