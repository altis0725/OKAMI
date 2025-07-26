"""
エンドツーエンドの進化フローをテストするモジュール
APIレスポンス → タスク実行 → 分析 → 改善提案 → 知識保存の流れを検証
"""

import pytest
import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# テスト対象のモジュールをインポート
from core.evolution_tracker import EvolutionTracker
from core.knowledge_manager import KnowledgeManager
from crews.crew_factory import CrewFactory
from evolution.improvement_applier import ImprovementApplier
from crewai import Crew, Agent, Task


class TestEvolutionFlow:
    """進化フローの統合テスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def evolution_tracker(self, temp_dir):
        """EvolutionTrackerのインスタンスを作成"""
        storage_dir = os.path.join(temp_dir, "evolution")
        return EvolutionTracker(storage_dir=storage_dir)
    
    @pytest.fixture
    def knowledge_manager(self, temp_dir):
        """KnowledgeManagerのインスタンスを作成"""
        knowledge_dir = os.path.join(temp_dir, "knowledge")
        return KnowledgeManager(knowledge_dir=knowledge_dir)
    
    @pytest.fixture
    def improvement_applier(self, temp_dir):
        """ImprovementApplierのインスタンスを作成"""
        return ImprovementApplier(base_path=temp_dir)
    
    def test_full_evolution_flow(self, temp_dir, evolution_tracker, knowledge_manager, improvement_applier):
        """
        完全な進化フローをテスト
        1. タスク実行とトラッキング
        2. パターン分析と改善提案生成
        3. 改善内容の知識保存
        4. 次回起動時の知識読み込み
        """
        # ステップ1: タスクの実行をシミュレート
        # 成功するタスク
        for i in range(3):
            evolution_tracker.track_task_execution(
                agent_role="research_agent",
                task_description="Research latest AI developments and trends",
                execution_time=15.0,
                success=True,
                output="Found 10 recent AI papers on transformer architectures...",
                task_id=f"task_success_{i}"
            )
        
        # 失敗するタスク（同じパターン）
        for i in range(5):
            evolution_tracker.track_task_execution(
                agent_role="research_agent",
                task_description="Research complex quantum computing algorithms",
                execution_time=45.0,
                success=False,
                output="Error: Unable to find sufficient information",
                task_id=f"task_fail_{i}"
            )
        
        # ステップ2: 改善提案の生成
        suggestions = evolution_tracker.get_improvement_suggestions()
        
        # 改善提案が生成されていることを確認
        assert len(suggestions) > 0
        assert any(s["type"] == "skill_improvement" for s in suggestions)
        assert any(s["type"] == "performance_optimization" for s in suggestions)
        
        # 学習インサイトも確認
        insights = evolution_tracker.get_recent_insights()
        assert len(insights) > 0
        
        # ステップ3: 改善内容を知識ファイルとして保存
        knowledge_dir = os.path.join(temp_dir, "knowledge")
        agents_dir = os.path.join(knowledge_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # 改善提案を知識として保存
        changes = []
        for suggestion in suggestions:
            if suggestion["agent_role"] != "system":
                # エージェント固有の改善を知識として保存
                knowledge_file = f"agents/{suggestion['agent_role']}_improvements.md"
                content = f"""
# Improvement for {suggestion['agent_role']}

## Issue: {suggestion['suggestion']}

### Recommended Actions:
"""
                for action in suggestion['details']['recommended_actions']:
                    content += f"- {action}\n"
                
                changes.append((knowledge_file, "add", {"content": content}))
        
        # ImprovementApplierで変更を適用
        results = improvement_applier.apply_changes(changes, dry_run=False)
        
        # 変更が正常に適用されたことを確認
        assert len(results["applied"]) > 0
        assert len(results["failed"]) == 0
        
        # ステップ4: 知識が保存されたことを確認
        research_improvements = os.path.join(agents_dir, "research_agent_improvements.md")
        assert os.path.exists(research_improvements)
        
        with open(research_improvements, "r") as f:
            content = f.read()
            assert "Improvement for research_agent" in content
            assert "Success rate:" in content
        
        # ステップ5: KnowledgeManagerで知識を再読み込み
        knowledge_manager.refresh_knowledge_from_directory(force_reload=True)
        
        # 知識が読み込まれたことを確認
        agent_sources = knowledge_manager.agent_sources.get("research_agent_improvements", [])
        assert len(agent_sources) > 0
        
        # ステップ6: CrewFactoryでの自動読み込みをシミュレート
        # 設定ディレクトリの準備
        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(os.path.join(config_dir, "agents"), exist_ok=True)
        os.makedirs(os.path.join(config_dir, "tasks"), exist_ok=True)
        os.makedirs(os.path.join(config_dir, "crews"), exist_ok=True)
        
        # 知識ディレクトリも正しいパスに設定
        os.environ["OKAMI_KNOWLEDGE_DIR"] = knowledge_dir
        
        # ダミーの設定ファイルを作成
        agent_config = {
            "research_agent": {
                "role": "Research Specialist",
                "goal": "Find accurate information",
                "backstory": "Expert researcher"
            }
        }
        with open(os.path.join(config_dir, "agents", "research_agent.yaml"), "w") as f:
            import yaml
            yaml.dump(agent_config, f)
        
        # CrewFactoryを初期化（知識が自動的に読み込まれる）
        with patch.dict(os.environ, {"MONICA_API_KEY": "test_key"}):
            factory = CrewFactory(config_dir=config_dir)
            factory._knowledge_manager = knowledge_manager
            
            # 知識が利用可能であることを確認
            stats = factory.refresh_knowledge()
            assert stats["total_agent_sources"] > 0
    
    def test_evolution_tracker_pattern_analysis(self, evolution_tracker):
        """EvolutionTrackerのパターン分析機能をテスト"""
        # 同じキーワードを含む失敗タスクを複数実行
        for i in range(5):
            evolution_tracker.track_task_execution(
                agent_role="writer_agent",
                task_description="Write comprehensive report on blockchain technology",
                execution_time=20.0,
                success=False,
                output="Failed to generate comprehensive content",
                task_id=f"blockchain_fail_{i}"
            )
        
        # パターンが検出されることを確認
        insights = evolution_tracker.get_recent_insights()
        failure_insights = [i for i in insights if i["type"] == "failure_pattern"]
        
        assert len(failure_insights) > 0
        assert "blockchain" in failure_insights[0]["metadata"]["common_keywords"]
    
    def test_improvement_applier_markdown(self, improvement_applier, temp_dir):
        """ImprovementApplierのMarkdown保存機能をテスト"""
        # 知識ディレクトリの作成
        knowledge_dir = os.path.join(temp_dir, "knowledge", "agents")
        os.makedirs(knowledge_dir, exist_ok=True)
        
        # 改善内容の適用
        changes = [
            ("knowledge/agents/test_agent.md", "add", {
                "content": "## Best Practices\n- Always validate input\n- Use structured output"
            })
        ]
        
        results = improvement_applier.apply_changes(changes, dry_run=False)
        
        # ファイルが作成されたことを確認
        test_file = os.path.join(temp_dir, "knowledge", "agents", "test_agent.md")
        assert os.path.exists(test_file)
        
        # 内容が正しく追加されたことを確認
        with open(test_file, "r") as f:
            content = f.read()
            assert "Best Practices" in content
            assert "Evolution Update" in content  # タイムスタンプ付きで追加される
    
    def test_knowledge_manager_reload(self, knowledge_manager, temp_dir):
        """KnowledgeManagerの再読み込み機能をテスト"""
        # 知識ファイルを作成
        agents_dir = os.path.join(temp_dir, "knowledge", "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        test_knowledge = """# Test Agent Knowledge
        
## Skills
- Data analysis
- Report generation
"""
        
        with open(os.path.join(agents_dir, "test_agent.md"), "w") as f:
            f.write(test_knowledge)
        
        # 知識を読み込み
        stats = knowledge_manager.refresh_knowledge_from_directory()
        
        # 読み込みが成功したことを確認
        assert stats["agent_knowledge_added"] > 0
        assert "test_agent" in stats["agents_with_knowledge"]
    
    @pytest.mark.asyncio
    async def test_async_task_execution_flow(self, evolution_tracker):
        """非同期タスク実行フローのテスト"""
        # 非同期でタスクを実行
        async def execute_task(task_id: str, success: bool):
            await asyncio.sleep(0.1)  # 非同期処理をシミュレート
            evolution_tracker.track_task_execution(
                agent_role="async_agent",
                task_description=f"Async task {task_id}",
                execution_time=0.1,
                success=success,
                output=f"Result for {task_id}",
                task_id=task_id
            )
        
        # 複数のタスクを並行実行
        tasks = []
        for i in range(10):
            success = i % 2 == 0  # 偶数は成功、奇数は失敗
            tasks.append(execute_task(f"async_{i}", success))
        
        await asyncio.gather(*tasks)
        
        # 結果が記録されていることを確認
        system_perf = evolution_tracker.get_system_performance()
        assert system_perf["total_tasks"] == 10
        assert system_perf["successful_tasks"] == 5
        assert system_perf["failed_tasks"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])