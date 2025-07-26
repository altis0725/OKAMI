"""
クルー全体の改善も含めて適用するスクリプト
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
    print("=== 改善内容の自動適用（クルー改善を含む） ===\n")
    
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
        
        # ファイルパスを決定
        if suggestion['agent_role'] == 'system':
            # システム全体の改善はcrewディレクトリに保存
            file_path = "knowledge/crew/system_improvements.md"
        else:
            # エージェント固有の改善
            file_path = f"knowledge/agents/{suggestion['agent_role']}.md"
        
        changes.append((file_path, "add", {"content": content}))
    
    if changes:
        print(f"\n適用する変更: {len(changes)}件")
        
        # crew改善とagent改善を分けて表示
        crew_changes = [c for c in changes if 'crew/' in c[0]]
        agent_changes = [c for c in changes if 'agents/' in c[0]]
        
        if crew_changes:
            print(f"  - クルー全体の改善: {len(crew_changes)}件")
        if agent_changes:
            print(f"  - エージェント個別の改善: {len(agent_changes)}件")
        
        # 変更を適用
        results = applier.apply_changes(changes, dry_run=False)
        
        print(f"\n✅ 適用完了:")
        print(f"  - 成功: {len(results['applied'])}件")
        print(f"  - 失敗: {len(results['failed'])}件")
        print(f"  - スキップ: {len(results['skipped'])}件")
        
        for applied in results['applied']:
            print(f"\n📝 更新されたファイル: {applied['file']}")
            
        # クルー改善ファイルの内容を確認
        crew_file = project_root / "knowledge/crew/system_improvements.md"
        if crew_file.exists():
            print(f"\n--- クルー全体の改善内容 ---")
            with open(crew_file, 'r') as f:
                content = f.read()
                # 最後の500文字を表示
                print(content[-500:] if len(content) > 500 else content)
            print("--- 終了 ---")
    
    print("\n完了！")


if __name__ == "__main__":
    main()