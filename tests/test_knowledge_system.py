#!/usr/bin/env python3
"""
新しい知識管理システムのテストスクリプト
EmbeddingManager、KnowledgeManager、自動読み込み機能をテスト
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.knowledge_manager import KnowledgeManager
from core.embedding_manager import get_embedding_manager, reset_embedding_manager
from utils.config import get_config
import structlog

# ログ設定
logger = structlog.get_logger()

def test_embedding_manager():
    """EmbeddingManagerのテスト"""
    print("\n=== EmbeddingManager Test ===")
    
    try:
        # EmbeddingManagerの初期化
        embedding_manager = get_embedding_manager()
        
        # ヘルスチェック
        is_healthy, status = embedding_manager.health_check()
        print(f"Health Check: {'✓' if is_healthy else '✗'} - {status}")
        
        if not is_healthy:
            print("EmbeddingManager is not healthy. Skipping embedding tests.")
            return False
        
        # 単一テキストのエンベディング
        test_text = "これはテスト用のテキストです。"
        embedding = embedding_manager.generate_single_embedding(test_text)
        print(f"Single embedding: {len(embedding)} dimensions")
        
        # バッチエンベディング
        test_texts = [
            "最初のテストテキスト",
            "二番目のテストテキスト", 
            "三番目のテストテキスト"
        ]
        embeddings = embedding_manager.generate_embeddings(test_texts)
        print(f"Batch embeddings: {len(embeddings)} embeddings, {len(embeddings[0]) if embeddings else 0} dimensions each")
        
        # 統計情報
        stats = embedding_manager.get_stats()
        print(f"Stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"EmbeddingManager test failed: {e}")
        return False

def test_knowledge_manager():
    """KnowledgeManagerのテスト"""
    print("\n=== KnowledgeManager Test ===")
    
    try:
        # 設定を読み込み
        config = get_config()
        
        # KnowledgeManagerの初期化
        km = KnowledgeManager(
            knowledge_dir=config.knowledge_dir,
            embedder_config=config.get_embedder_config()
        )
        
        # 手動で知識読み込みをテスト（エラーを詳しく見る）
        try:
            sources = km.load_knowledge_from_directory()
            print(f"Manual load successful: crew={len(sources['crew'])}, agents={len(sources['agents'])}")
            
            # 直接追加のテスト
            for source in sources['crew'][:1]:  # 最初の1つだけテスト
                print(f"Testing crew source: {type(source).__name__}, paths={getattr(source, 'file_paths', None)}")
                km.crew_sources.append(source)
                print("Direct append successful")
                
        except Exception as e:
            print(f"Manual load failed: {e}")
            import traceback
            traceback.print_exc()
        
        # 自動初期化のテスト
        success = km.auto_initialize_knowledge()
        print(f"Auto initialization: {'✓' if success else '✗'}")
        
        # 知識の動的読み込みテスト
        stats = km.refresh_knowledge_from_directory()
        print(f"Dynamic refresh stats: {stats}")
        
        # 知識ソースの確認
        crew_config = km.get_crew_knowledge_config()
        print(f"Crew knowledge sources: {len(crew_config.get('knowledge_sources', []))}")
        
        # エージェント知識の確認
        for agent_name in km.agent_sources.keys():
            agent_config = km.get_agent_knowledge_config(agent_name)
            print(f"Agent '{agent_name}' knowledge sources: {len(agent_config.get('knowledge_sources', []))}")
        
        # ファイルタイプ判定のテスト（拡張子のみでテスト）
        test_extensions = [
            (".md", "TextFileKnowledgeSource"),
            (".txt", "TextFileKnowledgeSource"),
            (".csv", "CSVKnowledgeSource"),
            (".json", "JSONKnowledgeSource"),
            (".xlsx", "ExcelKnowledgeSource"),
        ]
        
        print("\nFile type detection test:")
        for ext, expected_type in test_extensions:
            # テスト用のファイルを一時的に作成
            temp_file = Path(config.knowledge_dir) / f"test{ext}"
            temp_file.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイルタイプに応じた適切なコンテンツを作成
            if ext == ".json":
                content = '{"test": "content", "type": "json"}'
            elif ext == ".csv":
                content = "name,value\ntest,123\nsample,456"
            else:
                content = "# Test Content\nThis is test content for file type detection."
            
            temp_file.write_text(content)
            
            try:
                source = km.create_knowledge_source(str(temp_file))
                result = "✓" if type(source).__name__ == expected_type else "✗"
                print(f"  test{ext}: {type(source).__name__} {result}")
            except Exception as e:
                print(f"  test{ext}: Error - {e}")
            finally:
                # テストファイルを削除
                if temp_file.exists():
                    temp_file.unlink()
        
        # コレクション情報
        collections = km.list_collections()
        print(f"Available collections: {collections}")
        
        return True
        
    except Exception as e:
        print(f"KnowledgeManager test failed: {e}")
        return False

def test_crew_factory_integration():
    """CrewFactoryとの統合テスト"""
    print("\n=== CrewFactory Integration Test ===")
    
    try:
        from crews.crew_factory import CrewFactory
        
        # CrewFactoryの初期化（自動でKnowledgeManagerも初期化される）
        factory = CrewFactory()
        
        # 知識更新のテスト
        refresh_stats = factory.refresh_knowledge()
        print(f"Knowledge refresh via CrewFactory: {refresh_stats}")
        
        # 強制リロードのテスト
        force_refresh_stats = factory.refresh_knowledge(force_reload=True)
        print(f"Force refresh stats: {force_refresh_stats}")
        
        return True
        
    except Exception as e:
        print(f"CrewFactory integration test failed: {e}")
        return False

def test_knowledge_sources():
    """様々な知識ソースのテスト""" 
    print("\n=== Knowledge Sources Test ===")
    
    try:
        from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
        from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
        
        # StringKnowledgeSourceのテスト
        string_source = StringKnowledgeSource(
            content="これはテスト用の知識コンテンツです。CrewAI標準の知識ソースを使用しています。",
            chunk_size=100,
            chunk_overlap=20
        )
        print(f"StringKnowledgeSource created: {type(string_source).__name__}")
        
        # テスト用のファイルをknowledgeディレクトリ内に作成
        test_file = Path("knowledge/test_knowledge.md")
        test_content = """# Test Knowledge

## Section 1
This is test content for knowledge source testing.

## Section 2
CrewAI knowledge sources support various file formats.

## Section 3
The system can automatically detect and process different file types.
"""
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(test_content)
        
        try:
            # TextFileKnowledgeSourceのテスト（相対パスを使用）
            text_source = TextFileKnowledgeSource(
                file_paths=["test_knowledge.md"],  # knowledgeディレクトリからの相対パス
                chunk_size=200,
                chunk_overlap=50
            )
            print(f"TextFileKnowledgeSource created: {type(text_source).__name__}")
        finally:
            # テストファイルを削除
            if test_file.exists():
                test_file.unlink()
        
        return True
        
    except Exception as e:
        print(f"Knowledge sources test failed: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🚀 Starting OKAMI Knowledge System Tests")
    print("=" * 50)
    
    test_results = []
    
    # 各テストを実行
    tests = [
        ("EmbeddingManager", test_embedding_manager),
        ("KnowledgeManager", test_knowledge_manager),
        ("Knowledge Sources", test_knowledge_sources),
        ("CrewFactory Integration", test_crew_factory_integration),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
            print(f"\n{test_name}: {'✓ PASSED' if result else '✗ FAILED'}")
        except Exception as e:
            print(f"\n{test_name}: ✗ ERROR - {e}")
            test_results.append((test_name, False))
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Knowledge system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())