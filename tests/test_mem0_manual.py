#!/usr/bin/env python3
"""Mem0への手動保存テスト"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# 環境変数設定
os.environ['MEM0_API_KEY'] = 'm0-3QG2I8s47RQVV1943CV4LHFAwVZW9wAzIUXhLEGK'

def test_mem0_save_and_search():
    """Mem0に直接保存してから検索するテスト"""
    from mem0 import MemoryClient
    
    client = MemoryClient(api_key=os.environ['MEM0_API_KEY'])
    
    # 1. メッセージ形式でメモリを追加
    print("=== メモリ追加テスト ===")
    messages = [
        {"role": "user", "content": "The OKAMI system is a multi-agent AI system based on CrewAI."},
        {"role": "assistant", "content": "I understand that OKAMI is a multi-agent AI system built on CrewAI framework."}
    ]
    
    result = client.add(messages, user_id='okami_main_crew')
    print(f"追加結果: {result}")
    
    # 2. 検索
    print("\n=== 検索テスト ===")
    search_results = client.search("OKAMI", user_id='okami_main_crew')
    print(f"OKAMI検索結果: {len(search_results)}件")
    for r in search_results:
        print(f"  - {r.get('memory')}: score={r.get('score')}")
    
    # 3. 全メモリ取得
    print("\n=== 全メモリ取得 ===")
    all_memories = client.get_all(user_id='okami_main_crew')
    print(f"全メモリ数: {len(all_memories)}")
    for memory in all_memories:
        print(f"  - ID: {memory.get('id')}")
        print(f"    Memory: {memory.get('memory')}")
        print(f"    Created: {memory.get('created_at')}")

def test_crewai_memory_storage():
    """CrewAIのメモリストレージ方法を確認"""
    from crewai.memory.storage.mem0_storage import Mem0Storage
    
    print("\n=== CrewAI Mem0Storage テスト ===")
    
    # Mem0Storageを直接作成
    storage = Mem0Storage(
        embedder_config={
            "provider": "mem0",
            "config": {
                "user_id": "test_storage",
                "api_key": os.environ['MEM0_API_KEY']
            }
        }
    )
    
    # メモリを保存
    print("メモリ保存テスト...")
    storage.save(
        value="OKAMI system uses CrewAI for multi-agent orchestration",
        metadata={"type": "system_info", "source": "test"}
    )
    
    # 検索
    print("メモリ検索テスト...")
    results = storage.search("OKAMI", limit=5)
    print(f"検索結果: {results}")

if __name__ == "__main__":
    # Mem0直接テスト
    test_mem0_save_and_search()
    
    # CrewAI Mem0Storageテスト
    try:
        test_crewai_memory_storage()
    except Exception as e:
        print(f"CrewAI Mem0Storageエラー: {e}")
        import traceback
        traceback.print_exc()