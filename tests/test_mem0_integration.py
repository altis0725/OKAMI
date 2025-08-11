#!/usr/bin/env python3
"""Mem0統合テストスクリプト"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数設定
os.environ['MEM0_API_KEY'] = 'm0-3QG2I8s47RQVV1943CV4LHFAwVZW9wAzIUXhLEGK'
os.environ['MONICA_API_KEY'] = 'sk-1hNhe_Q4peALkeEWk75yP9GsXuR1kC1hUlaA3tFYP7uQS4H2Sj4fh7p4Iof5LMiwRAq8bw-4A8E7yEm0IFFaDt6bLHDE'
os.environ['MONICA_API_BASE'] = 'https://openapi.monica.im/v1'
os.environ['OPENAI_API_KEY'] = os.environ['MONICA_API_KEY']
os.environ['OPENAI_API_BASE'] = os.environ['MONICA_API_BASE']

def test_mem0_direct():
    """Mem0 APIへの直接アクセステスト"""
    print("\n=== Mem0 API直接アクセステスト ===")
    
    from mem0 import MemoryClient
    
    client = MemoryClient(api_key=os.environ['MEM0_API_KEY'])
    
    # テスト用メッセージ
    messages = [
        {"role": "user", "content": "OKAMIシステムのテストです"},
        {"role": "assistant", "content": "テストメモリを保存しました"}
    ]
    
    try:
        # メモリ追加
        result = client.add(messages, user_id='okami_test')
        print(f"メモリ追加結果: {result}")
        
        # メモリ検索
        search_results = client.search("OKAMI", user_id='okami_test')
        print(f"検索結果: {search_results}")
        
        # 全メモリ取得
        all_memories = client.get_all(user_id='okami_test')
        print(f"全メモリ数: {len(all_memories)}")
        for memory in all_memories[:3]:
            print(f"  - {memory}")
            
    except Exception as e:
        print(f"エラー: {e}")

def test_crew_with_mem0():
    """CrewAIでMem0を使用したテスト"""
    print("\n=== CrewAI Mem0統合テスト ===")
    
    from crews.crew_factory import CrewFactory
    from crewai import Agent, Task, Crew
    from crewai.llm import LLM
    
    # シンプルなテストクルーを作成
    try:
        # LLMの初期化
        monica_llm = LLM(
            model="gpt-4o",
            api_key=os.environ.get("MONICA_API_KEY"),
            base_url="https://openapi.monica.im/v1"
        )
        
        # ExternalMemoryの設定（Mem0用）
        from crewai.memory.external.external_memory import ExternalMemory
        
        # Mem0を使用する場合、embedder_configにMem0の設定全体を含める
        external_memory = ExternalMemory(
            embedder_config={
                "provider": "mem0",
                "config": {
                    "user_id": "okami_test_crew",
                    "api_key": os.environ['MEM0_API_KEY']
                }
            }
        )
        
        # シンプルなエージェントを作成
        test_agent = Agent(
            role="Memory Test Agent",
            goal="Test memory functionality",
            backstory="You are testing the OKAMI memory system",
            llm=monica_llm,
            verbose=True
        )
        
        # シンプルなタスクを作成
        test_task = Task(
            description="Remember this: The OKAMI system is working correctly with Mem0 integration. Today is a test day.",
            expected_output="Confirmation that the information has been understood and processed",
            agent=test_agent
        )
        
        # クルーを作成
        crew = Crew(
            agents=[test_agent],
            tasks=[test_task],
            memory=True,
            external_memory=external_memory,
            verbose=True
        )
        
        print(f"クルー名: Test Crew")
        print(f"メモリ有効: {crew.memory}")
        print(f"External Memory設定: あり")
        
        # タスクを実行
        print("\nタスク実行中...")
        result = crew.kickoff()
        print(f"実行結果: {result}")
        
        # メモリが保存されたか確認
        print("\n=== Mem0メモリ確認 ===")
        from mem0 import MemoryClient
        client = MemoryClient(api_key=os.environ['MEM0_API_KEY'])
        
        # 保存されたメモリを検索
        memories = client.get_all(user_id='okami_test_crew')
        print(f"保存されたメモリ数: {len(memories)}")
        for memory in memories[:10]:
            print(f"  - {memory.get('memory', memory)}")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

def check_mem0_memories():
    """既存のMem0メモリを確認"""
    print("\n=== 既存のMem0メモリ確認 ===")
    
    from mem0 import MemoryClient
    
    client = MemoryClient(api_key=os.environ['MEM0_API_KEY'])
    
    # 異なるuser_idでメモリを確認
    user_ids = ['okami_system', 'okami_main_crew', 'okami_test', 'evolution_crew']
    
    for user_id in user_ids:
        try:
            memories = client.get_all(user_id=user_id)
            if memories:
                print(f"\n{user_id}のメモリ数: {len(memories)}")
                for memory in memories[:3]:
                    print(f"  - {memory.get('memory', memory)}")
            else:
                print(f"{user_id}: メモリなし")
        except Exception as e:
            print(f"{user_id}: エラー - {e}")

if __name__ == "__main__":
    # Mem0 API直接テスト
    test_mem0_direct()
    
    # 既存メモリの確認
    check_mem0_memories()
    
    # CrewAI統合テスト
    test_crew_with_mem0()