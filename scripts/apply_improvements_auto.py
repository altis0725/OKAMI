"""
改善内容を自動的に適用するスクリプト
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.evolution_tracker import EvolutionTracker
from evolution.improvement_applier import ImprovementApplier


def main():
    """メイン実行"""
    print("=== 改善内容の自動適用 ===\n")
    
    # プロジェクトのパスを使用
    evolution_dir = project_root / "storage" / "evolution"
    
    # EvolutionTrackerから既存のデータを使用
    tracker = EvolutionTracker(storage_dir=str(evolution_dir))
    
    # 改善提案を生成
    print("改善提案の生成中...")
    suggestions = tracker.get_improvement_suggestions()
    print(f"生成された改善提案: {len(suggestions)}件\n")
    
    if not suggestions:
        print("改善提案がありません。")
        return
    
    # 改善内容を準備
    applier = ImprovementApplier(base_path=str(project_root))
    changes = []
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for suggestion in suggestions:
        if suggestion['agent_role'] not in ['system']:
            print(f"[{suggestion['priority']}] {suggestion['agent_role']}: {suggestion['suggestion']}")
            
            content = f"""
## Automated Improvement - {timestamp}

### Identified Issue
{suggestion['suggestion']}

### Recommended Improvements
"""
            for action in suggestion['details']['recommended_actions']:
                content += f"- {action}\n"
            
            if 'recent_failure_tasks' in suggestion['details']:
                content += "\n### Recent Failure Examples\n"
                for task in suggestion['details']['recent_failure_tasks'][:3]:
                    content += f"- {task}\n"
            
            # 既存のエージェント知識ファイルに追加
            file_path = f"knowledge/agents/{suggestion['agent_role']}.md"
            changes.append((file_path, "add", {"content": content}))
    
    if changes:
        print(f"\n適用する変更: {len(changes)}件")
        
        # 変更を適用
        results = applier.apply_changes(changes, dry_run=False)
        
        print(f"\n✅ 適用完了:")
        print(f"  - 成功: {len(results['applied'])}件")
        print(f"  - 失敗: {len(results['failed'])}件")
        print(f"  - スキップ: {len(results['skipped'])}件")
        
        for applied in results['applied']:
            print(f"\n📝 更新されたファイル: {applied['file']}")
            
        # 確認のために最初のファイルの内容を表示
        if results['applied']:
            first_file = results['applied'][0]['file']
            file_path = project_root / first_file
            if file_path.exists():
                print(f"\n--- {first_file} の最後の部分 ---")
                with open(file_path, 'r') as f:
                    content = f.read()
                    # 最後の500文字を表示
                    print(content[-500:] if len(content) > 500 else content)
                print("--- 終了 ---")
    
    print("\n完了！")


if __name__ == "__main__":
    main()