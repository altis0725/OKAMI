"""
グラフメモリ機能のテストスイート
"""

import pytest
import sys
from pathlib import Path
import json
import networkx as nx
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.graph_memory_manager import GraphMemoryManager
from core.knowledge_graph_integration import KnowledgeGraphIntegration
from core.memory_manager import MemoryManager
from core.knowledge_manager import KnowledgeManager


class TestGraphMemoryManager:
    """GraphMemoryManagerのテスト"""
    
    @pytest.fixture
    def graph_memory(self, tmp_path):
        """テスト用のGraphMemoryManagerインスタンス"""
        return GraphMemoryManager(storage_path=str(tmp_path / "graph_memory"))
    
    def test_initialization(self, graph_memory):
        """初期化のテスト"""
        assert graph_memory is not None
        assert isinstance(graph_memory.memory_graph, nx.DiGraph)
        assert graph_memory.memory_graph.number_of_nodes() == 0
        assert graph_memory.memory_graph.number_of_edges() == 0
    
    def test_add_memory_node(self, graph_memory):
        """メモリノード追加のテスト"""
        success = graph_memory.add_memory_node(
            node_id="test_node_1",
            node_type="task",
            content="Test task content",
            metadata={"priority": "high"}
        )
        
        assert success is True
        assert "test_node_1" in graph_memory.memory_graph
        node_data = graph_memory.memory_graph.nodes["test_node_1"]
        assert node_data["node_type"] == "task"
        assert node_data["content"] == "Test task content"
        assert node_data["metadata"]["priority"] == "high"
    
    def test_add_memory_relation(self, graph_memory):
        """メモリ関係追加のテスト"""
        # ノードを追加
        graph_memory.add_memory_node("agent_1", "agent", "Agent 1")
        graph_memory.add_memory_node("task_1", "task", "Task 1")
        
        # 関係を追加
        success = graph_memory.add_memory_relation(
            source_id="agent_1",
            target_id="task_1",
            relation_type="executed",
            context="Agent executed task",
            weight=1.0
        )
        
        assert success is True
        assert graph_memory.memory_graph.has_edge("agent_1", "task_1")
        edge_data = graph_memory.memory_graph["agent_1"]["task_1"]
        assert edge_data["relation_type"] == "executed"
        assert edge_data["context"] == "Agent executed task"
    
    def test_record_task_execution(self, graph_memory):
        """タスク実行記録のテスト"""
        graph_memory.record_task_execution(
            task_id="task_001",
            agent_name="research_agent",
            task_description="Research AI trends",
            result="Found 10 trending topics in AI",
            success=True
        )
        
        # ノードが作成されているか確認
        assert f"task_task_001" in graph_memory.memory_graph
        assert f"agent_research_agent" in graph_memory.memory_graph
        assert f"result_task_001" in graph_memory.memory_graph
        
        # 関係が作成されているか確認
        assert graph_memory.memory_graph.has_edge("agent_research_agent", "task_task_001")
        assert graph_memory.memory_graph.has_edge("task_task_001", "result_task_001")
    
    def test_search_memories(self, graph_memory):
        """メモリ検索のテスト"""
        # テストデータを追加
        graph_memory.add_memory_node("node_1", "task", "AI research task")
        graph_memory.add_memory_node("node_2", "result", "Machine learning results")
        graph_memory.add_memory_node("node_3", "concept", "Deep learning concept")
        
        # 検索実行
        results = graph_memory.search_memories(
            query="learning",
            limit=10
        )
        
        assert len(results) == 2  # "Machine learning" と "Deep learning"
        assert any(r["id"] == "node_2" for r in results)
        assert any(r["id"] == "node_3" for r in results)
    
    def test_find_related_memories(self, graph_memory):
        """関連メモリ検索のテスト"""
        # グラフ構造を作成
        graph_memory.add_memory_node("center", "task", "Central task")
        graph_memory.add_memory_node("related_1", "result", "Related result 1")
        graph_memory.add_memory_node("related_2", "concept", "Related concept 2")
        graph_memory.add_memory_node("unrelated", "task", "Unrelated task")
        
        graph_memory.add_memory_relation("center", "related_1", "produced")
        graph_memory.add_memory_relation("center", "related_2", "mentions")
        
        # 関連メモリを検索
        related = graph_memory.find_related_memories(
            node_id="center",
            max_depth=1,
            limit=10
        )
        
        assert len(related) == 2
        assert any(r["id"] == "related_1" for r in related)
        assert any(r["id"] == "related_2" for r in related)
        assert not any(r["id"] == "unrelated" for r in related)
    
    def test_get_agent_performance_history(self, graph_memory):
        """エージェントパフォーマンス履歴のテスト"""
        # エージェントのタスク実行を記録
        for i in range(5):
            graph_memory.record_task_execution(
                task_id=f"task_{i}",
                agent_name="test_agent",
                task_description=f"Task {i}",
                result=f"Result {i}",
                success=(i % 2 == 0)  # 偶数は成功、奇数は失敗
            )
        
        # パフォーマンス履歴を取得
        history = graph_memory.get_agent_performance_history("test_agent")
        
        assert history["agent_name"] == "test_agent"
        assert history["total_tasks"] == 5
        assert history["successful_tasks"] == 3  # 0, 2, 4が成功
        assert history["success_rate"] == 0.6
        assert len(history["recent_tasks"]) == 5
    
    def test_identify_knowledge_gaps(self, graph_memory):
        """知識ギャップ特定のテスト"""
        # 孤立したノードを作成
        graph_memory.add_memory_node("isolated_1", "concept", "Isolated concept")
        graph_memory.add_memory_node("isolated_2", "task", "Isolated task")
        
        # 小さなコンポーネントを作成
        graph_memory.add_memory_node("small_1", "agent", "Agent 1")
        graph_memory.add_memory_node("small_2", "task", "Task 1")
        graph_memory.add_memory_relation("small_1", "small_2", "executed")
        
        # ギャップを特定
        gaps = graph_memory.identify_knowledge_gaps()
        
        assert len(gaps) > 0
        isolated_gaps = [g for g in gaps if g["type"] == "isolated_knowledge"]
        assert len(isolated_gaps) == 2
        
        weak_gaps = [g for g in gaps if g["type"] == "weak_connection"]
        assert len(weak_gaps) >= 1
    
    def test_save_and_load_graph(self, graph_memory, tmp_path):
        """グラフの保存と読み込みのテスト"""
        # データを追加
        graph_memory.add_memory_node("node_1", "task", "Test task")
        graph_memory.add_memory_node("node_2", "result", "Test result")
        graph_memory.add_memory_relation("node_1", "node_2", "produced")
        
        # 保存
        graph_memory.save_memory_graph()
        
        # 新しいインスタンスで読み込み
        new_graph_memory = GraphMemoryManager(storage_path=str(tmp_path / "graph_memory"))
        
        assert new_graph_memory.memory_graph.number_of_nodes() == 2
        assert new_graph_memory.memory_graph.number_of_edges() == 1
        assert "node_1" in new_graph_memory.memory_graph
        assert "node_2" in new_graph_memory.memory_graph
    
    def test_get_graph_statistics(self, graph_memory):
        """グラフ統計情報のテスト"""
        # テストデータを追加
        graph_memory.add_memory_node("agent_1", "agent", "Agent 1")
        graph_memory.add_memory_node("task_1", "task", "Task 1")
        graph_memory.add_memory_node("task_2", "task", "Task 2")
        graph_memory.add_memory_node("result_1", "result", "Result 1")
        
        graph_memory.add_memory_relation("agent_1", "task_1", "executed")
        graph_memory.add_memory_relation("agent_1", "task_2", "executed")
        graph_memory.add_memory_relation("task_1", "result_1", "produced")
        
        # 統計情報を取得
        stats = graph_memory.get_graph_statistics()
        
        assert stats["total_nodes"] == 4
        assert stats["total_edges"] == 3
        assert stats["node_types"]["agent"] == 1
        assert stats["node_types"]["task"] == 2
        assert stats["node_types"]["result"] == 1
        assert stats["relation_types"]["executed"] == 2
        assert stats["relation_types"]["produced"] == 1
        assert stats["average_degree"] > 0


class TestKnowledgeGraphIntegration:
    """KnowledgeGraphIntegrationのテスト"""
    
    @pytest.fixture
    def integration(self, tmp_path):
        """テスト用の統合インスタンス"""
        knowledge_manager = KnowledgeManager(
            knowledge_dir=str(tmp_path / "knowledge"),
            embedder_config={"provider": "openai", "config": {}}
        )
        graph_memory = GraphMemoryManager(
            storage_path=str(tmp_path / "graph_memory")
        )
        return KnowledgeGraphIntegration(
            knowledge_manager=knowledge_manager,
            graph_memory=graph_memory
        )
    
    def test_process_task_result(self, integration):
        """タスク結果処理のテスト"""
        result = integration.process_task_result(
            task_id="test_001",
            agent_name="test_agent",
            task_description="Analyze data patterns",
            result="Found 3 significant patterns in the dataset",
            success=True
        )
        
        assert result["task_id"] == "test_001"
        assert result["memory_recorded"] is True
        assert result["knowledge_extracted"] is True
        
        # グラフメモリに記録されているか確認
        graph_nodes = integration.graph_memory.memory_graph.nodes()
        assert f"task_test_001" in graph_nodes
        assert f"agent_test_agent" in graph_nodes
    
    def test_enhanced_search(self, integration):
        """拡張検索のテスト"""
        # テストデータを追加
        integration.graph_memory.add_memory_node(
            "mem_1", "task", "Machine learning research"
        )
        integration.graph_memory.add_memory_node(
            "mem_2", "concept", "Deep learning algorithms"
        )
        
        # 検索実行
        results = integration.enhanced_search(
            query="learning",
            search_memory=True,
            search_knowledge=True,
            limit=10
        )
        
        assert "query" in results
        assert results["query"] == "learning"
        assert "memory_results" in results
        assert len(results["memory_results"]) > 0
        assert "knowledge_results" in results
        assert "combined_relevance" in results
    
    def test_get_context_for_agent(self, integration):
        """エージェント用コンテキスト取得のテスト"""
        # エージェントの過去の実行を記録
        integration.graph_memory.record_task_execution(
            task_id="past_001",
            agent_name="research_agent",
            task_description="Previous research task",
            result="Research completed",
            success=True
        )
        
        # コンテキストを取得
        context = integration.get_context_for_agent(
            agent_name="research_agent",
            task_description="New research task",
            max_items=5
        )
        
        assert context["agent"] == "research_agent"
        assert context["task"] == "New research task"
        assert "relevant_memories" in context
        assert "relevant_knowledge" in context
        assert "past_performance" in context
        assert "suggestions" in context
    
    def test_analyze_system_knowledge_state(self, integration):
        """システム知識状態分析のテスト"""
        # いくつかのデータを追加
        integration.graph_memory.add_memory_node("node_1", "task", "Task 1")
        integration.graph_memory.add_memory_node("node_2", "result", "Result 1")
        integration.graph_memory.add_memory_node("isolated", "concept", "Isolated")
        
        # 分析実行
        analysis = integration.analyze_system_knowledge_state()
        
        assert "timestamp" in analysis
        assert "memory_statistics" in analysis
        assert "knowledge_gaps" in analysis
        assert "recommendations" in analysis
        
        stats = analysis["memory_statistics"]
        assert stats["total_nodes"] == 3
        
        # 推奨事項があるはず
        assert len(analysis["recommendations"]) > 0


class TestMemoryManagerIntegration:
    """MemoryManagerとの統合テスト"""
    
    @pytest.fixture
    def memory_manager(self, tmp_path):
        """テスト用のMemoryManagerインスタンス"""
        import os
        os.environ["CREWAI_STORAGE_DIR"] = str(tmp_path)
        return MemoryManager(
            storage_path=str(tmp_path / "memory"),
            use_graph_memory=True
        )
    
    def test_graph_memory_initialization(self, memory_manager):
        """グラフメモリの初期化テスト"""
        assert memory_manager.graph_memory is not None
        assert memory_manager.kg_integration is not None
        assert isinstance(memory_manager.graph_memory, GraphMemoryManager)
        assert isinstance(memory_manager.kg_integration, KnowledgeGraphIntegration)
    
    def test_record_task_in_graph(self, memory_manager):
        """グラフへのタスク記録テスト"""
        memory_manager.record_task_in_graph(
            task_id="integration_001",
            agent_name="writer_agent",
            task_description="Write documentation",
            result="Documentation completed",
            success=True
        )
        
        # グラフに記録されているか確認
        assert f"task_integration_001" in memory_manager.graph_memory.memory_graph
        assert f"agent_writer_agent" in memory_manager.graph_memory.memory_graph
    
    def test_search_graph_memory(self, memory_manager):
        """グラフメモリ検索テスト"""
        # データを追加
        memory_manager.graph_memory.add_memory_node(
            "search_test", "task", "Search optimization task"
        )
        
        # 検索実行
        results = memory_manager.search_graph_memory(
            query="optimization",
            limit=5
        )
        
        assert len(results) > 0
        assert any(r["id"] == "search_test" for r in results)
    
    def test_get_enhanced_memory_config(self, memory_manager):
        """拡張メモリ設定取得テスト"""
        config = memory_manager.get_enhanced_memory_config()
        
        assert "graph_memory" in config
        assert config["graph_memory"]["enabled"] is True
        assert "storage_path" in config["graph_memory"]
        assert "statistics" in config["graph_memory"]
    
    def test_reset_graph_memory(self, memory_manager):
        """グラフメモリリセットテスト"""
        # データを追加
        memory_manager.graph_memory.add_memory_node("temp", "task", "Temporary")
        assert memory_manager.graph_memory.memory_graph.number_of_nodes() > 0
        
        # リセット実行
        memory_manager.reset_memory(memory_type="graph")
        
        # グラフが空になっているか確認
        assert memory_manager.graph_memory.memory_graph.number_of_nodes() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])