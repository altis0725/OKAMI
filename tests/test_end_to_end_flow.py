"""
エンドツーエンドの進化フローテスト
実際のシステムの動作を再現
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.evolution_tracker import EvolutionTracker
from core.knowledge_manager import KnowledgeManager
from evolution.improvement_applier import ImprovementApplier


def main():
    """メインのテスト実行"""
    print("=== OKAMIシステム進化フローのエンドツーエンドテスト ===\n")
    
    # 一時ディレクトリでテスト環境を構築
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"テスト環境: {temp_dir}\n")
        
        # ディレクトリ構造を作成
        evolution_dir = os.path.join(temp_dir, "storage", "evolution")
        knowledge_dir = os.path.join(temp_dir, "knowledge")
        agents_knowledge_dir = os.path.join(knowledge_dir, "agents")
        
        os.makedirs(evolution_dir, exist_ok=True)
        os.makedirs(agents_knowledge_dir, exist_ok=True)
        
        # ステップ1: EvolutionTrackerでタスク実行を記録
        print("ステップ1: タスク実行の記録")
        print("-" * 50)
        
        tracker = EvolutionTracker(storage_dir=evolution_dir)
        
        # 様々なタスクを実行
        tasks = [
            # 成功タスク
            ("research_agent", "Research latest AI trends", True, 15.0, "Found 20 relevant papers"),
            ("research_agent", "Analyze market data", True, 12.0, "Market analysis completed"),
            ("writer_agent", "Write summary report", True, 20.0, "Report generated successfully"),
            
            # 失敗タスク（パターンを作る）
            ("research_agent", "Research quantum computing algorithms", False, 45.0, "Insufficient data"),
            ("research_agent", "Find quantum mechanics papers", False, 50.0, "Failed to access sources"),
            ("research_agent", "Quantum cryptography research", False, 48.0, "Timeout error"),
            ("writer_agent", "Generate technical documentation", False, 60.0, "Failed to compile"),
            ("writer_agent", "Create API documentation", False, 55.0, "Template not found"),
        ]
        
        for i, (agent, desc, success, time, output) in enumerate(tasks):
            tracker.track_task_execution(
                agent_role=agent,
                task_description=desc,
                execution_time=time,
                success=success,
                output=output,
                task_id=f"task_{i}"
            )
            print(f"  ✓ タスク記録: {agent} - {desc[:30]}... ({'成功' if success else '失敗'})")
        
        # ステップ2: パターン分析と改善提案の生成
        print("\n\nステップ2: パターン分析と改善提案")
        print("-" * 50)
        
        # 改善提案を取得
        suggestions = tracker.get_improvement_suggestions()
        print(f"生成された改善提案: {len(suggestions)}件\n")
        
        for suggestion in suggestions:
            print(f"[{suggestion['priority']}] {suggestion['type']}")
            print(f"  対象: {suggestion['agent_role']}")
            print(f"  提案: {suggestion['suggestion']}")
            if 'recent_failure_tasks' in suggestion['details']:
                print(f"  失敗タスク例: {suggestion['details']['recent_failure_tasks'][0]}")
            print()
        
        # 学習インサイトも確認
        insights = tracker.get_recent_insights()
        print(f"\n学習インサイト: {len(insights)}件")
        for insight in insights[:3]:
            print(f"  - [{insight['type']}] {insight['description'][:60]}...")
        
        # ステップ3: 改善内容を知識として保存
        print("\n\nステップ3: 改善内容の知識保存")
        print("-" * 50)
        
        applier = ImprovementApplier(base_path=temp_dir)
        changes = []
        
        # 各エージェントの改善内容を準備
        for suggestion in suggestions:
            if suggestion['agent_role'] != 'system':
                content = f"""# {suggestion['agent_role']} Improvements

## Generated: {Path(__file__).name}

### Issue Identified
{suggestion['suggestion']}

### Recommended Actions
"""
                for action in suggestion['details']['recommended_actions']:
                    content += f"- {action}\n"
                
                content += f"\n### Performance Metrics\n"
                content += f"- Current success rate: {suggestion['details'].get('success_rate', 'N/A')}\n"
                content += f"- Average execution time: {suggestion['details'].get('current_avg_time', 'N/A')}s\n"
                
                file_path = f"knowledge/agents/{suggestion['agent_role']}_improvements.md"
                changes.append((file_path, "add", {"content": content}))
        
        # 変更を適用
        if changes:
            results = applier.apply_changes(changes, dry_run=False)
            print(f"適用結果: 成功={len(results['applied'])}, 失敗={len(results['failed'])}")
            
            for applied in results['applied']:
                print(f"  ✓ ファイル作成: {applied['file']}")
        
        # ステップ4: 知識の再読み込みと確認
        print("\n\nステップ4: 知識の読み込み確認")
        print("-" * 50)
        
        # KnowledgeManagerを初期化して知識を読み込み
        km = KnowledgeManager(knowledge_dir=knowledge_dir)
        
        # 手動で知識ファイルを確認
        print("\n作成された知識ファイル:")
        for file_path in Path(agents_knowledge_dir).glob("*.md"):
            print(f"  - {file_path.name}")
            with open(file_path, "r") as f:
                content = f.read()
                print(f"    内容プレビュー: {content[:100].strip()}...")
        
        # 知識の読み込みを試行
        try:
            stats = km.refresh_knowledge_from_directory()
            if "error" not in stats:
                print(f"\n知識読み込み成功:")
                print(f"  - エージェント知識: {stats.get('agent_knowledge_added', 0)}件")
                print(f"  - 合計知識ソース: {stats.get('total_agent_sources', 0)}件")
            else:
                print(f"\n知識読み込みエラー: {stats['error']}")
        except Exception as e:
            print(f"\n知識読み込み例外: {e}")
        
        # ステップ5: 進化レポートの生成
        print("\n\nステップ5: 進化レポート")
        print("-" * 50)
        
        report = tracker.generate_evolution_report()
        print(f"システムパフォーマンス:")
        print(f"  - 総タスク数: {report['system_performance']['total_tasks']}")
        print(f"  - 成功率: {report['system_performance']['success_rate']:.1%}")
        print(f"  - 改善率: {report['evolution_metrics']['improvement_rate']:.1%}")
        print(f"  - 学習速度: {report['evolution_metrics']['learning_velocity']:.2f}")
        
        # 最終確認
        print("\n\n=== テスト結果サマリー ===")
        print(f"✅ タスク実行記録: {len(tasks)}件")
        print(f"✅ 改善提案生成: {len(suggestions)}件")
        print(f"✅ 知識ファイル作成: {len(results['applied']) if changes else 0}件")
        print(f"✅ 学習インサイト: {len(insights)}件")
        
        # 成功判定
        success = (
            len(suggestions) > 0 and
            len(insights) > 0 and
            (not changes or len(results['applied']) > 0)
        )
        
        if success:
            print("\n🎉 エンドツーエンドテスト成功！")
            print("システムは正常に動作しています。")
        else:
            print("\n❌ テストに問題があります。")
            print("詳細なログを確認してください。")
        
        return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)