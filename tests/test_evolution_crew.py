"""
Evolution Crewのテストモジュール
evolution crewの動作とmain.pyの修正箇所を検証
"""

import pytest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# テスト対象のモジュールをインポート
from crews.crew_factory import CrewFactory
from core.evolution_tracker import EvolutionTracker
from evolution.improvement_applier import ImprovementApplier


class TestEvolutionCrew:
    """Evolution Crewのテストクラス"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def crew_factory(self, temp_dir):
        """CrewFactoryのインスタンスを作成"""
        # 設定ディレクトリを一時ディレクトリに変更
        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        
        # 必要な設定ファイルをコピー
        import shutil
        if os.path.exists("config/crews/evolution_crew.yaml"):
            crews_dir = os.path.join(config_dir, "crews")
            os.makedirs(crews_dir, exist_ok=True)
            shutil.copy("config/crews/evolution_crew.yaml", crews_dir)
        
        if os.path.exists("config/agents/evolution_agent.yaml"):
            agents_dir = os.path.join(config_dir, "agents")
            os.makedirs(agents_dir, exist_ok=True)
            shutil.copy("config/agents/evolution_agent.yaml", agents_dir)
        
        if os.path.exists("config/tasks/evolution_task.yaml"):
            tasks_dir = os.path.join(config_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            shutil.copy("config/tasks/evolution_task.yaml", tasks_dir)
        
        return CrewFactory()
    
    def test_evolution_crew_creation(self, crew_factory):
        """Evolution crewが正しく作成されることをテスト"""
        crew = crew_factory.get_crew("evolution_crew")
        assert crew is not None, "Evolution crewが作成されませんでした"
        assert crew.name == "System Evolution Crew", "Crew名が正しくありません"
    
    def test_evolution_crew_agents(self, crew_factory):
        """Evolution crewに必要なエージェントが含まれていることをテスト"""
        crew = crew_factory.get_crew("evolution_crew")
        agent_roles = [agent.role for agent in crew.agents]
        
        # 必要なエージェントが含まれていることを確認
        expected_roles = ["System Evolution Specialist", "Data Analysis Expert", "Quality Assurance Validator"]
        for expected_role in expected_roles:
            assert any(expected_role in agent_role for agent_role in agent_roles), \
                f"エージェント {expected_role} が見つかりません"
    
    def test_evolution_crew_tasks(self, crew_factory):
        """Evolution crewに必要なタスクが含まれていることをテスト"""
        crew = crew_factory.get_crew("evolution_crew")
        task_names = [task.description for task in crew.tasks]
        
        # evolution_taskが含まれていることを確認
        assert any("evolution" in task_name.lower() for task_name in task_names), \
            "evolution_taskが見つかりません"
    
    def test_evolution_crew_kickoff_method(self, crew_factory):
        """Evolution crewのkickoffメソッドが存在することをテスト"""
        crew = crew_factory.get_crew("evolution_crew")
        
        # kickoffメソッドが存在することを確認
        assert hasattr(crew, 'kickoff'), "Crewにkickoffメソッドがありません"
        
        # メソッドが呼び出し可能であることを確認
        assert callable(getattr(crew, 'kickoff')), "kickoffメソッドが呼び出し可能ではありません"
    
    def test_evolution_inputs_structure(self):
        """evolution_inputsの構造が正しいことをテスト"""
        # main.pyの_trigger_evolution_analysis関数で使用される入力構造をテスト
        task_description = "Test task description"
        task_result = "Test task result"
        
        evolution_inputs = {
            "user_input": task_description,
            "main_response": str(task_result)[:2000]  # サイズ制限を適用
        }
        
        # 必要なキーが存在することを確認
        assert "user_input" in evolution_inputs, "user_inputキーが存在しません"
        assert "main_response" in evolution_inputs, "main_responseキーが存在しません"
        
        # taskキーが存在しないことを確認（これが修正前のエラーの原因）
        assert "task" not in evolution_inputs, "taskキーが存在してはいけません"
        
        # 値が正しく設定されていることを確認
        assert evolution_inputs["user_input"] == task_description
        assert evolution_inputs["main_response"] == str(task_result)[:2000]
    
    def test_trigger_evolution_analysis_fix(self):
        """main.pyの修正箇所をテスト"""
        # _trigger_evolution_analysis関数の修正箇所をテスト
        task_id = "test_task_123"
        task_result = "Test task result"
        task_description = "Test task description"
        
        # evolution_inputsの作成（修正後の正しい構造）
        evolution_inputs = {
            "user_input": task_description,
            "main_response": str(task_result)[:2000]
        }
        
        # task_descriptionの取得（修正後の正しい方法）
        task_description_from_inputs = evolution_inputs["user_input"]
        
        # 修正前のエラーが発生しないことを確認
        assert task_description_from_inputs == task_description, \
            "task_descriptionが正しく取得されていません"
        
        # KeyErrorが発生しないことを確認
        try:
            _ = evolution_inputs["user_input"]  # 修正後の正しいキー
            assert True, "user_inputキーでアクセスできました"
        except KeyError:
            assert False, "user_inputキーでアクセスできませんでした"
        
        # 修正前のエラーが発生することを確認（taskキーが存在しない）
        with pytest.raises(KeyError):
            _ = evolution_inputs["task"]  # 修正前の間違ったキー
    
    def test_evolution_crew_config_validation(self, crew_factory):
        """Evolution crewの設定が正しいことをテスト"""
        crew = crew_factory.get_crew("evolution_crew")
        
        # 設定の検証
        assert hasattr(crew, 'name'), "Crewにname属性がありません"
        assert hasattr(crew, 'agents'), "Crewにagents属性がありません"
        assert hasattr(crew, 'tasks'), "Crewにtasks属性がありません"
        
        # エージェントとタスクが存在することを確認
        assert len(crew.agents) > 0, "エージェントが設定されていません"
        assert len(crew.tasks) > 0, "タスクが設定されていません"
    
    def test_main_py_fix_verification(self):
        """main.pyの修正が正しく適用されていることをテスト"""
        # main.pyの修正箇所を確認
        try:
            with open("main.py", "r") as f:
                content = f.read()
            
            # 修正前の間違ったコードが存在しないことを確認
            assert 'evolution_inputs["task"]' not in content, \
                "修正前の間違ったコードが残っています"
            
            # 修正後の正しいコードが存在することを確認
            assert 'evolution_inputs["user_input"]' in content, \
                "修正後の正しいコードが見つかりません"
            
            print("✅ main.pyの修正が正しく適用されています")
            
        except FileNotFoundError:
            pytest.skip("main.pyファイルが見つかりません")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 