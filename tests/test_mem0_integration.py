"""
Mem0統合のテスト
CrewAI 0.157.0対応のエラー許容モード実装の検証
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.mem0_helper import Mem0StatusChecker, mem0_error_handler, get_memory_config_for_crew
from core.memory_manager import MemoryManager
from crews.crew_factory import CrewFactory


class TestMem0StatusChecker(unittest.TestCase):
    """Mem0StatusCheckerのテスト"""
    
    def test_check_mem0_availability_without_api_key(self):
        """APIキーなしでのステータスチェック"""
        with patch.dict(os.environ, {}, clear=True):
            status = Mem0StatusChecker.check_mem0_availability()
            
            self.assertFalse(status["api_key_present"])
            self.assertFalse(status["connection_ok"])
            self.assertTrue(status["fallback_enabled"])
            self.assertIn("MEM0_API_KEY not set", status["warnings"])
    
    def test_check_mem0_availability_with_invalid_api_key(self):
        """無効なAPIキーでのステータスチェック"""
        with patch.dict(os.environ, {"MEM0_API_KEY": "invalid_key"}):
            # mem0パッケージのインポートを直接モック
            import sys
            mock_mem0 = MagicMock()
            mock_mem0.MemoryClient = MagicMock
            sys.modules['mem0'] = mock_mem0
            
            # MemoryClientをモック
            mock_client = MagicMock()
            mock_client.search.side_effect = Exception("401 Unauthorized")
            mock_mem0.MemoryClient.return_value = mock_client
            
            status = Mem0StatusChecker.check_mem0_availability()
            
            self.assertTrue(status["api_key_present"])
            self.assertFalse(status["connection_ok"])
            self.assertIn("Connection test failed", str(status["errors"]))
    
    def test_check_mem0_availability_with_local_mode(self):
        """ローカルモードでのステータスチェック"""
        with patch.dict(os.environ, {"USE_LOCAL_MEM0": "true"}):
            with patch("requests.get") as mock_get:
                # Ollamaが利用可能な場合をシミュレート
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "models": [{"name": "nomic-embed-text:latest"}]
                }
                mock_get.return_value = mock_response
                
                status = Mem0StatusChecker.check_mem0_availability()
                
                self.assertTrue(status["local_mode_enabled"])
                self.assertTrue(status.get("ollama_available", False))
    
    def test_print_status_report(self):
        """ステータスレポートの出力テスト"""
        status = {
            "ready": True,
            "mode": "basic",
            "api_key_present": False,
            "local_mode_enabled": False,
            "fallback_enabled": True,
            "error_tolerance": "high",
            "errors": ["Test error"],
            "warnings": ["Test warning"],
            "recommendations": ["Test recommendation"],
            "connection_ok": False
        }
        
        # 出力テスト（例外が発生しないことを確認）
        try:
            Mem0StatusChecker.print_status_report(status)
        except Exception as e:
            self.fail(f"print_status_report raised {e}")


class TestMem0ErrorHandler(unittest.TestCase):
    """mem0_error_handlerデコレータのテスト"""
    
    def test_error_handler_catches_exceptions(self):
        """エラーハンドラーが例外をキャッチすることを確認"""
        
        @mem0_error_handler
        def test_function():
            raise Exception("400 Bad Request")
        
        result = test_function()
        self.assertIsNone(result)
    
    def test_error_handler_returns_normal_value(self):
        """正常時は通常の値を返すことを確認"""
        
        @mem0_error_handler
        def test_function():
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")


class TestMemoryManager(unittest.TestCase):
    """MemoryManagerのテスト"""
    
    def test_memory_manager_without_mem0(self):
        """Mem0なしでのMemoryManager初期化"""
        with patch.dict(os.environ, {}, clear=True):
            manager = MemoryManager(
                use_mem0=False,
                fallback_to_basic=True
            )
            
            self.assertFalse(manager.mem0_initialized)
            self.assertIsNone(manager.external_memory)
            
            # 基本メモリ設定を取得
            config = manager.get_crew_memory_config()
            self.assertTrue(config["memory"])
            self.assertEqual(config["memory_config"]["provider"], "basic")
    
    def test_memory_manager_with_fallback(self):
        """フォールバック機能のテスト"""
        with patch.dict(os.environ, {"MEM0_API_KEY": "test_key"}):
            with patch("core.memory_manager.ExternalMemory") as mock_external:
                # ExternalMemoryの初期化で例外を発生させる
                mock_external.side_effect = Exception("Initialization failed")
                
                manager = MemoryManager(
                    use_mem0=True,
                    fallback_to_basic=True
                )
                
                self.assertFalse(manager.mem0_initialized)
                self.assertIsNone(manager.external_memory)
                
                # フォールバックで基本メモリが使用される
                config = manager.get_crew_memory_config()
                self.assertTrue(config["memory"])
                self.assertEqual(config["memory_config"]["provider"], "basic")
    
    def test_memory_manager_status_check(self):
        """ステータスチェック機能のテスト"""
        manager = MemoryManager(
            use_mem0=False,
            fallback_to_basic=True
        )
        
        status = manager.check_mem0_status()
        
        self.assertIn("memory_manager_state", status)
        self.assertFalse(status["memory_manager_state"]["initialized"])
        self.assertFalse(status["memory_manager_state"]["external_memory_active"])
    
    @patch("core.memory_manager.ExternalMemory")
    def test_memory_operations_with_error_handling(self, mock_external):
        """メモリ操作のエラーハンドリングテスト"""
        manager = MemoryManager(
            use_mem0=True,
            fallback_to_basic=True
        )
        
        # save_memoryのテスト（エラーハンドラーによりNoneが返される）
        result = manager.save_memory("test_key", "test_value")
        self.assertFalse(result)  # mem0_initializedがFalseのため
        
        # search_memoryのテスト（エラーハンドラーにより空リストが返される）
        results = manager.search_memory("test_query")
        self.assertEqual(results, [])


class TestCrewFactory(unittest.TestCase):
    """CrewFactoryのテスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        self.factory = None
    
    def tearDown(self):
        """テストのクリーンアップ"""
        if self.factory:
            self.factory = None
    
    @patch("crews.crew_factory.MemoryManager")
    def test_crew_factory_initialization(self, mock_memory_manager):
        """CrewFactoryの初期化テスト"""
        mock_memory_manager.return_value = MagicMock()
        
        factory = CrewFactory()
        
        # MemoryManagerが適切な引数で初期化されることを確認
        mock_memory_manager.assert_called_with(
            use_graph_memory=True,
            use_mem0=True,
            fallback_to_basic=True,
            mem0_config={
                "user_id": "okami_system",
                "fallback_to_basic": True
            }
        )
    
    @patch("crews.crew_factory.yaml.safe_load")
    @patch("builtins.open")
    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.exists")
    def test_crew_creation_with_mem0_config(self, mock_exists, mock_glob, mock_open, mock_yaml):
        """Mem0設定を持つクルーの作成テスト"""
        # モックの設定
        mock_exists.return_value = True
        mock_glob.return_value = []
        mock_yaml.return_value = {}
        
        # MONICA_API_KEYも含めて環境変数を設定
        with patch.dict(os.environ, {"MEM0_API_KEY": "test_key", "MONICA_API_KEY": "test_monica_key"}):
            factory = CrewFactory()
            
            # crew_configsに直接テスト用の設定を追加
            factory.crew_configs["test_crew"] = {
                "agents": [],
                "tasks": [],
                "process": "sequential",
                "mem0_config": {
                    "user_id": "test_user"
                }
            }
            
            with patch.object(factory, "create_agent", return_value=None):
                with patch.object(factory, "create_task", return_value=None):
                    with patch("crews.crew_factory.Crew") as mock_crew:
                        crew = factory.create_crew("test_crew")
                        
                        # Crewが作成されることを確認
                        mock_crew.assert_called_once()
                        
                        # メモリ設定が含まれることを確認
                        call_args = mock_crew.call_args[1]
                        self.assertTrue(call_args.get("memory", False))


class TestGetMemoryConfigForCrew(unittest.TestCase):
    """get_memory_config_for_crew関数のテスト"""
    
    def test_get_memory_config_without_mem0(self):
        """Mem0なしでの設定生成"""
        config = get_memory_config_for_crew(
            use_mem0=False,
            fallback_to_basic=True
        )
        
        self.assertFalse(config["use_mem0"])
        self.assertTrue(config["fallback_to_basic"])
        self.assertEqual(config["user_id"], "okami_system")
    
    def test_get_memory_config_with_local_mode(self):
        """ローカルモードでの設定生成"""
        with patch.dict(os.environ, {"USE_LOCAL_MEM0": "true"}):
            config = get_memory_config_for_crew(
                use_mem0=True,
                fallback_to_basic=True
            )
            
            self.assertTrue(config["use_mem0"])
            self.assertIn("local_mem0_config", config)
            self.assertEqual(
                config["local_mem0_config"]["embedder"]["provider"],
                "ollama"
            )


class TestIntegrationFlow(unittest.TestCase):
    """統合フローのテスト"""
    
    def test_complete_flow_without_mem0(self):
        """Mem0なしでの完全なフローテスト"""
        with patch.dict(os.environ, {}, clear=True):
            # 1. ステータスチェック
            status = Mem0StatusChecker.check_mem0_availability()
            self.assertFalse(status["api_key_present"])
            
            # 2. MemoryManager初期化
            manager = MemoryManager(
                use_mem0=True,  # Mem0を試みるが、APIキーなしでフォールバック
                fallback_to_basic=True
            )
            self.assertFalse(manager.mem0_initialized)
            
            # 3. メモリ設定の取得
            config = manager.get_crew_memory_config()
            self.assertEqual(config["memory_config"]["provider"], "basic")
            
            print("\n✅ Integration test completed successfully without Mem0")
    
    def test_complete_flow_with_mock_mem0(self):
        """モックMem0での完全なフローテスト"""
        with patch.dict(os.environ, {"MEM0_API_KEY": "test_key"}):
            with patch("core.memory_manager.ExternalMemory") as mock_external:
                # ExternalMemoryのモック設定
                mock_instance = MagicMock()
                mock_external.return_value = mock_instance
                
                # 1. MemoryManager初期化（成功をシミュレート）
                manager = MemoryManager(
                    use_mem0=True,
                    fallback_to_basic=True
                )
                
                # Mem0が初期化されたことを確認
                self.assertTrue(manager.mem0_initialized)
                self.assertIsNotNone(manager.external_memory)
                
                # 2. メモリ設定の取得
                config = manager.get_crew_memory_config()
                self.assertIn("external_memory", config)
                
                print("\n✅ Integration test completed successfully with mock Mem0")


def run_tests():
    """テストを実行"""
    # テストスイートの作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 各テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestMem0StatusChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestMem0ErrorHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryManager))
    suite.addTests(loader.loadTestsFromTestCase(TestCrewFactory))
    suite.addTests(loader.loadTestsFromTestCase(TestGetMemoryConfigForCrew))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationFlow))
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果のサマリー
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)