#!/usr/bin/env python
"""
グラフメモリ機能のデモスクリプト
メモリをグラフ構造で管理する機能のデモンストレーション
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.graph_memory_manager import GraphMemoryManager
from core.knowledge_graph_integration import KnowledgeGraphIntegration
from core.memory_manager import MemoryManager


def demonstrate_graph_memory():
    """グラフメモリの基本機能をデモンストレーション"""
    
    print("=" * 60)
    print("🧠 OKAMI Graph Memory System Demo")
    print("=" * 60)
    print()
    
    # GraphMemoryManagerの初期化
    print("📊 Initializing Graph Memory Manager...")
    graph_memory = GraphMemoryManager(storage_path="storage/demo_graph_memory")
    
    # 初期状態を表示
    stats = graph_memory.get_graph_statistics()
    print(f"Initial state: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
    print()
    
    # タスク実行を記録
    print("📝 Recording task executions...")
    tasks = [
        {
            "task_id": "research_001",
            "agent_name": "research_agent",
            "task_description": "Research the latest AI trends in 2025",
            "result": "Found 5 major trends: Multi-modal AI, Agentic AI, Smaller models, AI safety, and Edge AI",
            "success": True
        },
        {
            "task_id": "analysis_001",
            "agent_name": "analysis_agent",
            "task_description": "Analyze the impact of multi-modal AI on business",
            "result": "Multi-modal AI is transforming customer service, content creation, and data analysis",
            "success": True
        },
        {
            "task_id": "writer_001",
            "agent_name": "writer_agent",
            "task_description": "Write a summary report on AI trends",
            "result": "Report completed with executive summary and detailed analysis",
            "success": True
        }
    ]
    
    for task in tasks:
        graph_memory.record_task_execution(**task)
        print(f"  ✅ Recorded: {task['task_description'][:50]}...")
    
    print()
    
    # グラフの状態を表示
    stats = graph_memory.get_graph_statistics()
    print(f"After recording: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
    print(f"Node types: {stats['node_types']}")
    print(f"Relation types: {stats['relation_types']}")
    print()
    
    # メモリ検索
    print("🔍 Searching memories...")
    search_query = "AI"
    results = graph_memory.search_memories(query=search_query, limit=5)
    print(f"Search for '{search_query}' found {len(results)} results:")
    for result in results[:3]:
        print(f"  - {result['node_type']}: {result['content'][:60]}...")
    print()
    
    # 関連メモリの探索
    print("🕸️ Finding related memories...")
    if results:
        node_id = results[0]['id']
        related = graph_memory.find_related_memories(
            node_id=node_id,
            max_depth=2,
            limit=5
        )
        print(f"Found {len(related)} memories related to '{node_id}':")
        for rel in related[:3]:
            print(f"  - {rel['node_type']} ({rel['distance']} hops): {rel['content'][:50]}...")
    print()
    
    # エージェントのパフォーマンス履歴
    print("📈 Agent performance history...")
    for agent_name in ["research_agent", "analysis_agent", "writer_agent"]:
        history = graph_memory.get_agent_performance_history(agent_name)
        if history.get('total_tasks', 0) > 0:
            print(f"  {agent_name}:")
            print(f"    - Total tasks: {history['total_tasks']}")
            print(f"    - Success rate: {history['success_rate']:.0%}")
    print()
    
    # 知識ギャップの特定
    print("🔍 Identifying knowledge gaps...")
    gaps = graph_memory.identify_knowledge_gaps()
    if gaps:
        print(f"Found {len(gaps)} knowledge gaps:")
        for gap in gaps[:3]:
            print(f"  - {gap['type']}: {gap['suggestion']}")
    else:
        print("  No significant knowledge gaps found")
    print()
    
    # グラフの保存
    print("💾 Saving graph to disk...")
    graph_memory.save_memory_graph()
    print("  Graph saved successfully")
    print()
    
    return graph_memory


def demonstrate_integration():
    """知識グラフ統合のデモンストレーション"""
    
    print("=" * 60)
    print("🔗 Knowledge-Graph Integration Demo")
    print("=" * 60)
    print()
    
    # 統合システムの初期化
    print("🚀 Initializing integrated system...")
    memory_manager = MemoryManager(
        storage_path="storage/demo_memory",
        use_graph_memory=True
    )
    
    if not memory_manager.graph_memory:
        print("  ⚠️ Graph memory not available")
        return
    
    print("  ✅ Memory Manager initialized with graph memory")
    print()
    
    # タスクをグラフに記録
    print("📊 Recording task in graph...")
    memory_manager.record_task_in_graph(
        task_id="demo_001",
        agent_name="demo_agent",
        task_description="Demonstrate integration features",
        result="Integration successful with all components working",
        success=True
    )
    print("  ✅ Task recorded in graph memory")
    print()
    
    # グラフメモリを検索
    print("🔍 Searching graph memory...")
    results = memory_manager.search_graph_memory(
        query="integration",
        limit=5
    )
    print(f"  Found {len(results)} results")
    for result in results:
        print(f"    - {result.get('node_type', 'unknown')}: {result.get('content', '')[:50]}...")
    print()
    
    # 拡張メモリ設定を取得
    print("⚙️ Enhanced memory configuration:")
    config = memory_manager.get_enhanced_memory_config()
    if "graph_memory" in config:
        graph_config = config["graph_memory"]
        print(f"  - Enabled: {graph_config['enabled']}")
        print(f"  - Storage: {graph_config['storage_path']}")
        if 'statistics' in graph_config:
            stats = graph_config['statistics']
            print(f"  - Nodes: {stats.get('total_nodes', 0)}")
            print(f"  - Edges: {stats.get('total_edges', 0)}")
    print()


def main():
    """メイン実行関数"""
    
    print("\n🚀 Starting OKAMI Graph Memory Demo\n")
    
    # 基本的なグラフメモリのデモ
    graph_memory = demonstrate_graph_memory()
    
    # 統合機能のデモ
    demonstrate_integration()
    
    print("=" * 60)
    print("✨ Demo completed successfully!")
    print("=" * 60)
    print()
    
    # 最終統計
    final_stats = graph_memory.get_graph_statistics()
    print("📊 Final statistics:")
    print(f"  - Total nodes: {final_stats['total_nodes']}")
    print(f"  - Total edges: {final_stats['total_edges']}")
    print(f"  - Connected components: {final_stats['connected_components']}")
    print(f"  - Average degree: {final_stats['average_degree']:.2f}")
    print()
    
    print("💡 Graph memory enables:")
    print("  - Structured memory storage with relationships")
    print("  - Semantic search across memories")
    print("  - Performance tracking for agents")
    print("  - Knowledge gap identification")
    print("  - Context-aware task execution")
    print()


if __name__ == "__main__":
    main()