"""
Test knowledge loader functionality
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge.knowledge_loader import KnowledgeLoader, get_knowledge_loader, get_knowledge_for_crew


def test_load_all_knowledge():
    """Test loading all knowledge files"""
    print("Testing load_all_knowledge...")
    
    loader = KnowledgeLoader()
    knowledge = loader.load_all_knowledge()
    
    print(f"\n✓ Loaded {len(knowledge)} knowledge sources:")
    for key, content in knowledge.items():
        print(f"  - {key}: {len(content)} characters")
        # Show first line
        first_line = content.split('\n')[0] if content else "(empty)"
        print(f"    First line: {first_line}")


def test_get_combined_knowledge():
    """Test getting combined knowledge"""
    print("\n\nTesting get_combined_knowledge...")
    
    loader = KnowledgeLoader()
    combined = loader.get_combined_knowledge()
    
    print(f"\n✓ Combined knowledge: {len(combined)} characters")
    print(f"  Lines: {len(combined.split('\\n'))}")
    
    # Show section headers
    print("\n  Sections found:")
    for line in combined.split('\n'):
        if line.startswith("===") and line.endswith("==="):
            print(f"    {line}")


def test_search_knowledge():
    """Test searching knowledge"""
    print("\n\nTesting search_knowledge...")
    
    loader = KnowledgeLoader()
    
    # Test searches
    test_queries = [
        "error",
        "memory",
        "tool",
        "quality"
    ]
    
    for query in test_queries:
        results = loader.search_knowledge(query)
        print(f"\n✓ Search for '{query}': {len(results)} results")
        
        # Show first result
        if results:
            first = results[0]
            print(f"  First match in {first['source']} at line {first['line_number']}")
            print(f"  Matched line: {first['matched_line'].strip()}")


def test_get_knowledge_for_crew():
    """Test crew knowledge integration"""
    print("\n\nTesting get_knowledge_for_crew...")
    
    knowledge = get_knowledge_for_crew()
    
    print(f"\n✓ Crew knowledge ready: {len(knowledge)} characters")
    
    # Check that all expected sections are present
    expected_sections = [
        "GENERAL GUIDELINES",
        "BEST PRACTICES",
        "ERROR PATTERNS"
    ]
    
    print("\n  Expected sections:")
    for section in expected_sections:
        if section in knowledge:
            print(f"    ✓ {section}")
        else:
            print(f"    ✗ {section} (missing)")


def main():
    """Run all tests"""
    print("=== Knowledge Loader Tests ===\n")
    
    try:
        test_load_all_knowledge()
        test_get_combined_knowledge()
        test_search_knowledge()
        test_get_knowledge_for_crew()
        
        print("\n\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()