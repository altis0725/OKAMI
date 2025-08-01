#!/usr/bin/env python3
"""
Mem0の基本的な動作テスト
"""

import os
from dotenv import load_dotenv
from crewai import Crew, Agent, Task
from crewai.memory.external.external_memory import ExternalMemory

# .envファイルを読み込み
load_dotenv()

def test_mem0_basic_memory():
    """Mem0のbasic memory統合をテスト"""
    
    print("=== Mem0 Basic Memory テスト ===")
    
    # 環境変数からmem0のAPIキーを取得
    mem0_api_key = os.getenv("MEM0_API_KEY")
    print(f"Mem0 API Key: {mem0_api_key[:10]}..." if mem0_api_key else "API Key not found")
    
    # テスト用のエージェントとタスクを作成
    agent = Agent(
        role="Test Agent",
        goal="Test goal",
        backstory="Test backstory",
        memory=True
    )
    
    task = Task(
        description="Test task for mem0 integration",
        expected_output="Test output",
        agent=agent
    )
    
    try:
        # Mem0メモリ設定でクルーを作成
        crew = Crew(
            agents=[agent],
            tasks=[task],
            memory=True,
            external_memory=ExternalMemory(
                embedder_config={
                    "provider": "mem0",
                    "config": {
                        "user_id": "test_user_okami",
                        "api_key": mem0_api_key
                    }
                }
            )
        )
        
        print("✅ Crew created successfully with mem0 external memory")
        print(f"Memory enabled: {crew.memory}")
        
        # クルーの実行をテスト
        result = crew.kickoff()
        print(f"✅ Crew execution completed: {result}")
        
    except Exception as e:
        print(f"❌ Error creating crew with mem0: {e}")
        return False
    
    return True

def test_mem0_connection():
    """Mem0への接続をテスト"""
    
    print("\n=== Mem0 Connection テスト ===")
    
    try:
        import mem0
        
        # mem0ライブラリが利用可能かチェック
        print("✅ mem0 library available")
        
        # APIキーの確認
        api_key = os.getenv("MEM0_API_KEY")
        if api_key:
            print(f"✅ API Key found: {api_key[:10]}...")
        else:
            print("❌ API Key not found")
            return False
            
    except ImportError:
        print("❌ mem0 library not available")
        return False
    
    return True

if __name__ == "__main__":
    print("Mem0統合テストを開始します...")
    
    # 接続テスト
    if test_mem0_connection():
        print("✅ Mem0 connection test passed")
    else:
        print("❌ Mem0 connection test failed")
        exit(1)
    
    # Basic memoryテスト
    if test_mem0_basic_memory():
        print("✅ Mem0 basic memory test passed")
    else:
        print("❌ Mem0 basic memory test failed")
        exit(1)
    
    print("\n🎉 すべてのテストが成功しました！") 