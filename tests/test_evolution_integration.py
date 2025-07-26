"""
シンプルな統合テスト - 進化フローの主要コンポーネントを検証
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime

from core.evolution_tracker import EvolutionTracker
from core.knowledge_manager import KnowledgeManager
from evolution.improvement_applier import ImprovementApplier


def test_evolution_flow_integration():
    """進化フローの統合テスト：タスク実行 → 分析 → 改善提案 → 知識保存"""
    
    # 一時ディレクトリの設定
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. EvolutionTrackerでタスクを記録
        evolution_tracker = EvolutionTracker(storage_dir=os.path.join(temp_dir, "evolution"))
        
        # 成功タスクを記録
        for i in range(3):
            evolution_tracker.track_task_execution(
                agent_role="research_agent",
                task_description="Research AI trends and developments",
                execution_time=10.0,
                success=True,
                output="Successfully found relevant AI research papers",
                task_id=f"success_{i}"
            )
        
        # 失敗タスクを記録（パターンを作るため）
        for i in range(5):
            evolution_tracker.track_task_execution(
                agent_role="research_agent",
                task_description="Research complex quantum computing algorithms implementation",
                execution_time=50.0,
                success=False,
                output="Failed to find sufficient information",
                task_id=f"fail_{i}"
            )
        
        # 2. 改善提案を生成
        suggestions = evolution_tracker.get_improvement_suggestions()
        print(f"\n改善提案数: {len(suggestions)}")
        for s in suggestions:
            print(f"- {s['type']}: {s['suggestion']}")
        
        assert len(suggestions) > 0, "改善提案が生成されていません"
        
        # 3. 改善内容を知識として保存
        knowledge_dir = os.path.join(temp_dir, "knowledge")
        agents_dir = os.path.join(knowledge_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        improvement_applier = ImprovementApplier(base_path=temp_dir)
        
        # 改善提案を知識ファイルとして保存
        changes = []
        for suggestion in suggestions:
            if suggestion["agent_role"] != "system":
                content = f"""
# Improvement for {suggestion['agent_role']}

## Issue
{suggestion['suggestion']}

## Actions
"""
                for action in suggestion['details']['recommended_actions']:
                    content += f"- {action}\n"
                
                changes.append((
                    f"knowledge/agents/{suggestion['agent_role']}_improvements.md",
                    "add",
                    {"content": content}
                ))
        
        # 変更を適用
        results = improvement_applier.apply_changes(changes, dry_run=False)
        print(f"\n適用結果: 成功={len(results['applied'])}, 失敗={len(results['failed'])}")
        
        assert len(results["applied"]) > 0, "改善内容の適用に失敗しました"
        
        # 4. 知識が保存されたことを確認
        improvements_file = os.path.join(agents_dir, "research_agent_improvements.md")
        assert os.path.exists(improvements_file), "改善ファイルが作成されていません"
        
        with open(improvements_file, "r") as f:
            content = f.read()
            print(f"\n保存された改善内容:\n{content[:200]}...")
            assert "Improvement for research_agent" in content
            assert "Success rate:" in content
        
        # 5. KnowledgeManagerで知識を読み込み
        knowledge_manager = KnowledgeManager(knowledge_dir=knowledge_dir)
        stats = knowledge_manager.refresh_knowledge_from_directory()
        
        print(f"\n知識読み込み統計: {stats}")
        assert stats["agent_knowledge_added"] > 0, "知識が読み込まれていません"
        
        # 6. 学習インサイトも確認
        insights = evolution_tracker.get_recent_insights()
        print(f"\n学習インサイト数: {len(insights)}")
        for insight in insights[:3]:
            print(f"- {insight['type']}: {insight['description']}")
        
        assert len(insights) > 0, "学習インサイトが生成されていません"
        
        print("\n✅ 進化フローの統合テストが成功しました！")
        print("  - タスク実行の記録 ✓")
        print("  - パターン分析と改善提案 ✓")
        print("  - 改善内容の知識保存 ✓")
        print("  - 知識の再読み込み ✓")


if __name__ == "__main__":
    test_evolution_flow_integration()