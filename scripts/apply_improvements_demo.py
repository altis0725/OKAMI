"""
実際のプロジェクトディレクトリに改善を適用するデモスクリプト
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
    print("=== 改善内容を実際のknowledgeディレクトリに適用するデモ ===\n")
    
    # プロジェクトのパスを使用
    evolution_dir = project_root / "storage" / "evolution"
    knowledge_dir = project_root / "knowledge"
    
    print(f"プロジェクトルート: {project_root}")
    print(f"知識ディレクトリ: {knowledge_dir}\n")
    
    # EvolutionTrackerを初期化
    tracker = EvolutionTracker(storage_dir=str(evolution_dir))
    
    # デモ用のタスク実行を記録
    print("ステップ1: デモ用タスクの実行記録")
    print("-" * 50)
    
    demo_tasks = [
        # research_agentの改善が必要なケース（5件以上必要）
        ("research_agent", "Research blockchain implementation patterns", False, 65.0, 
         "Timeout: Unable to gather comprehensive information"),
        ("research_agent", "Analyze blockchain consensus mechanisms", False, 70.0,
         "Error: Insufficient technical depth in sources"),
        ("research_agent", "Research blockchain scalability solutions", False, 68.0,
         "Failed: Could not access required technical papers"),
        ("research_agent", "Study blockchain security vulnerabilities", False, 72.0,
         "Error: Access denied to security databases"),
        ("research_agent", "Research DeFi protocols architecture", False, 69.0,
         "Failed: Complex technical concepts not fully analyzed"),
        ("research_agent", "Analyze smart contract patterns", True, 25.0,
         "Successfully identified common patterns"),
        
        # writer_agentの改善が必要なケース（5件以上必要）
        ("writer_agent", "Generate blockchain technical documentation", False, 80.0,
         "Error: Unable to structure complex technical content"),
        ("writer_agent", "Create blockchain API documentation", False, 75.0,
         "Failed: Template processing error"),
        ("writer_agent", "Write smart contract documentation", False, 78.0,
         "Error: Technical terms not properly explained"),
        ("writer_agent", "Generate DeFi protocol guide", False, 82.0,
         "Failed: Unable to simplify complex concepts"),
        ("writer_agent", "Create blockchain tutorial", False, 77.0,
         "Error: Missing key technical details"),
        ("writer_agent", "Write executive summary", True, 30.0,
         "Successfully created concise summary"),
    ]
    
    for i, (agent, task, success, time, output) in enumerate(demo_tasks):
        tracker.track_task_execution(
            agent_role=agent,
            task_description=task,
            execution_time=time,
            success=success,
            output=output,
            task_id=f"demo_{datetime.now().strftime('%Y%m%d')}_{i}"
        )
        print(f"  ✓ {agent}: {task[:40]}... ({'成功' if success else '失敗'})")
    
    # 改善提案を生成
    print("\n\nステップ2: 改善提案の生成")
    print("-" * 50)
    
    suggestions = tracker.get_improvement_suggestions()
    print(f"生成された改善提案: {len(suggestions)}件\n")
    
    for suggestion in suggestions:
        print(f"[{suggestion['priority']}] {suggestion['agent_role']}")
        print(f"  {suggestion['suggestion']}\n")
    
    # 改善内容を実際のknowledgeディレクトリに適用
    print("\nステップ3: 改善内容の適用")
    print("-" * 50)
    
    applier = ImprovementApplier(base_path=str(project_root))
    changes = []
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for suggestion in suggestions:
        if suggestion['agent_role'] not in ['system']:
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
        print(f"\n適用する変更:")
        for path, action, _ in changes:
            print(f"  - {path} ({action})")
        
        # ドライランモードで確認
        print("\n[DRY RUN] 以下の内容が追加されます:")
        results_dry = applier.apply_changes(changes, dry_run=True)
        
        response = input("\n実際に適用しますか？ (y/N): ")
        if response.lower() == 'y':
            results = applier.apply_changes(changes, dry_run=False)
            print(f"\n✅ 適用完了: 成功={len(results['applied'])}, 失敗={len(results['failed'])}")
            
            for applied in results['applied']:
                print(f"  - {applied['file']}: {applied['status']}")
        else:
            print("\n適用をキャンセルしました。")
    else:
        print("\n適用する改善提案がありません。")
    
    print("\n完了！")


if __name__ == "__main__":
    main()