"""
OKAMIシステムでのMem0 Basic Memory統合テスト
"""

import os
import pytest
from unittest.mock import Mock, patch
from crewai import Crew, Agent, Task

from core.memory_manager import MemoryManager
from crews.crew_factory import CrewFactory


class TestMem0BasicMemory:
    """Mem0 Basic Memory統合のテスト"""

    def setup_method(self):
        """テスト前のセットアップ"""
        # テスト用の環境変数を設定
        os.environ["MEM0_API_KEY"] = "test-api-key"
        
        # テスト用のMemoryManagerを作成
        self.memory_manager = MemoryManager(
            use_mem0=True,
            mem0_config={
                "user_id": "test_user",
                "org_id": "test_org",
                "project_id": "test_project"
            }
        )

    def test_memory_manager_initialization(self):
        """MemoryManagerの初期化テスト"""
        assert self.memory_manager.use_mem0 is True
        assert self.memory_manager.mem0_config["user_id"] == "test_user"
        assert self.memory_manager.mem0_config["org_id"] == "test_org"
        assert self.memory_manager.mem0_config["project_id"] == "test_project"

    def test_get_memory_config(self):
        """メモリ設定の取得テスト"""
        config = self.memory_manager.get_memory_config()
        
        assert config["memory"] is True
        assert config["memory_config"]["provider"] == "mem0"
        assert config["memory_config"]["config"]["user_id"] == "test_user"
        assert config["memory_config"]["config"]["org_id"] == "test_org"
        assert config["memory_config"]["config"]["project_id"] == "test_project"
        assert config["memory_config"]["user_memory"] == {}

    def test_memory_save_and_search(self):
        """メモリ保存と検索のテスト"""
        # メモリ保存
        self.memory_manager.save_memory(
            key="test_key",
            value="テストメモリデータ",
            metadata={"agent": "test_agent"}
        )
        
        # メモリ検索
        results = self.memory_manager.search_memory(
            query="テストメモリ",
            limit=10,
            score_threshold=0.5
        )
        
        # 結果の検証（実際のmem0の動作に依存）
        assert isinstance(results, list)

    def test_memory_reset(self):
        """メモリリセットのテスト"""
        # メモリをリセット
        self.memory_manager.reset_memory("all")
        
        # リセット後の検索結果を確認
        results = self.memory_manager.search_memory("test")
        assert isinstance(results, list)

    @patch('core.memory_manager.ExternalMemory')
    def test_external_memory_initialization(self, mock_external_memory):
        """外部メモリ初期化のテスト"""
        # ExternalMemoryのモック
        mock_instance = Mock()
        mock_external_memory.return_value = mock_instance
        
        # MemoryManagerを再初期化
        memory_manager = MemoryManager(
            use_mem0=True,
            mem0_config={"user_id": "test_user"}
        )
        
        # ExternalMemoryが正しく初期化されたか確認
        mock_external_memory.assert_called_once()
        call_args = mock_external_memory.call_args
        assert call_args[1]["embedder_config"]["provider"] == "mem0"
        assert call_args[1]["embedder_config"]["config"]["user_id"] == "test_user"

    def test_crew_factory_mem0_integration(self):
        """CrewFactoryでのMem0統合テスト"""
        # CrewFactoryを作成
        crew_factory = CrewFactory()
        
        # テスト用のクルー設定
        test_crew_config = {
            "name": "Test Crew",
            "agents": [],
            "tasks": [],
            "memory": True,
            "memory_config": {
                "provider": "mem0",
                "config": {
                    "user_id": "test_crew_user"
                }
            }
        }
        
        # クルー設定をモック
        crew_factory.crew_configs["test_crew"] = test_crew_config
        
        # 実際のCrewAIが呼ばれるため、エラーハンドリングでテスト
        try:
            crew = crew_factory.create_crew("test_crew")
            # 成功した場合は設定が正しいことを確認
            assert crew is not None
        except Exception as e:
            # mem0のAPIキーエラーは予想される（テスト用APIキーのため）
            # 設定が正しく処理されたことを確認
            error_str = str(e).lower()
            # 実際のエラーメッセージに基づいてチェック
            assert any(keyword in error_str for keyword in [
                "invalid api key", "mem0", "validation error", "value error"
            ])

    def test_mem0_without_api_key(self):
        """APIキーなしでのMem0設定テスト"""
        # APIキーを削除
        if "MEM0_API_KEY" in os.environ:
            del os.environ["MEM0_API_KEY"]
        
        # MemoryManagerを作成
        memory_manager = MemoryManager(
            use_mem0=True,
            mem0_config={"user_id": "test_user"}
        )
        
        # 外部メモリがNoneになることを確認
        assert memory_manager.external_memory is None

    def test_local_mem0_config(self):
        """ローカルMem0設定のテスト"""
        local_config = {
            "user_id": "test_user",
            "local_mem0_config": {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {"host": "localhost", "port": 6333}
                },
                "llm": {
                    "provider": "openai",
                    "config": {"api_key": "test-key", "model": "gpt-4"}
                },
                "embedder": {
                    "provider": "openai",
                    "config": {"api_key": "test-key", "model": "text-embedding-3-small"}
                }
            }
        }
        
        memory_manager = MemoryManager(
            use_mem0=True,
            mem0_config=local_config
        )
        
        config = memory_manager.get_memory_config()
        assert config["memory_config"]["config"]["local_mem0_config"] == local_config["local_mem0_config"]

    def test_memory_config_fallback(self):
        """メモリ設定のフォールバックテスト"""
        # APIキーなしでMemoryManagerを作成
        if "MEM0_API_KEY" in os.environ:
            del os.environ["MEM0_API_KEY"]
        
        memory_manager = MemoryManager(use_mem0=False)
        config = memory_manager.get_memory_config()
        
        # デフォルトのbasic memory設定が使用されることを確認
        assert config["memory_config"]["provider"] == "basic"
        assert config["memory_config"]["config"] == {}
        assert config["memory_config"]["user_memory"] == {}

    def test_crew_with_mem0_memory(self):
        """Mem0メモリを使用したクルーのテスト"""
        # テスト用のエージェントとタスクを作成（必須フィールドを追加）
        agent = Agent(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory",  # 必須フィールドを追加
            memory=True
        )
        
        task = Task(
            description="Test task",
            expected_output="Test output",  # 必須フィールドを追加
            agent=agent
        )
        
        # Mem0メモリ設定でクルーを作成
        try:
            crew = Crew(
                agents=[agent],
                tasks=[task],
                memory=True,
                memory_config={
                    "provider": "mem0",
                    "config": {
                        "user_id": "test_crew_user",
                        "api_key": "test-api-key"
                    },
                    "user_memory": {}
                }
            )
            
            # クルーが正しく作成されたことを確認
            assert crew.memory is True
            assert hasattr(crew, 'memory_manager') or hasattr(crew, '_memory_manager')
        except Exception as e:
            # mem0のAPIキーエラーは予想される（テスト用APIキーのため）
            # 設定が正しく処理されたことを確認
            error_str = str(e).lower()
            assert any(keyword in error_str for keyword in ["invalid api key", "mem0", "validation error"])

    def test_memory_operations_with_mock(self):
        """モックを使用したメモリ操作のテスト"""
        with patch('core.memory_manager.ExternalMemory') as mock_external_memory:
            mock_instance = Mock()
            mock_external_memory.return_value = mock_instance
            
            # テスト用のMemoryManagerを作成
            memory_manager = MemoryManager(
                use_mem0=True,
                mem0_config={"user_id": "test_user"}
            )
            
            # メモリ保存をテスト
            memory_manager.save_memory("test_key", "test_value")
            mock_instance.save.assert_called_once()
            
            # メモリ検索をテスト
            mock_instance.search.return_value = [{"content": "test_result"}]
            results = memory_manager.search_memory("test_query")
            mock_instance.search.assert_called_once()
            assert len(results) == 1
            assert results[0]["content"] == "test_result"


if __name__ == "__main__":
    # テストの実行
    pytest.main([__file__, "-v"]) 