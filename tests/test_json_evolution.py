#!/usr/bin/env python3
"""JSON形式での自己成長機能テスト"""

import json
from pathlib import Path
from datetime import datetime

# システムパスの設定
import sys
sys.path.append(str(Path(__file__).parent))

from crews.crew_factory import CrewFactory
from evolution.improvement_parser import ImprovementParser
from evolution.improvement_applier import ImprovementApplier

def test_json_evolution():
    """JSON形式での自己成長機能テスト"""
    print("=== JSON Evolution Test ===")
    
    # CrewFactoryを初期化
    crew_factory = CrewFactory()
    
    # Evolution Crewを取得
    evolution_crew = crew_factory.get_crew("evolution_crew")
    if not evolution_crew:
        print("Error: Evolution crew not found")
        return
    
    # テスト用のタスク
    test_input = {
        "task": """Based on the previous task execution, analyze and provide improvement suggestions.

Previous task: Simple research task about CrewAI features
Result: The research agent provided general information but lacked specific details.

Analyze this and provide specific improvements in JSON format as requested."""
    }
    
    print("\nExecuting Evolution Crew...")
    try:
        # Evolution Crewを実行
        result = evolution_crew.kickoff(inputs=test_input)
        result_str = str(result)
        
        print(f"\nRaw result (first 500 chars): {result_str[:500]}...")
        
        # JSON部分を抽出
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_str, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)
            print(f"\nExtracted JSON: {json_str}")
            
            # JSONをパース
            try:
                json_data = json.loads(json_str)
                print(f"\nParsed JSON successfully!")
                print(f"Number of changes: {len(json_data.get('changes', []))}")
                
                # 各変更を表示
                for i, change in enumerate(json_data.get('changes', [])):
                    print(f"\nChange {i+1}:")
                    print(f"  Type: {change.get('type')}")
                    print(f"  Target: {change.get('agent', change.get('file'))}")
                    print(f"  Reason: {change.get('reason')}")
                    
            except json.JSONDecodeError as e:
                print(f"\nJSON parse error: {e}")
        else:
            print("\nNo JSON block found in the output")
            
    except Exception as e:
        print(f"\nError executing Evolution Crew: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_json_evolution()