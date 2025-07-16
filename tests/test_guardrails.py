"""
Test guardrail functionality
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails import (
    ResponseQualityGuardrail,
    FactualAccuracyGuardrail,
    SafetyGuardrail,
    create_quality_guardrail,
    create_safety_guardrail,
    create_accuracy_guardrail
)


def test_quality_guardrail():
    """Test response quality guardrail"""
    print("Testing ResponseQualityGuardrail...")
    
    guardrail = create_quality_guardrail(min_score=7.0)
    
    test_cases = [
        ("This is a high-quality, comprehensive response that addresses the user's needs effectively.", True),
        ("Too short", False),
        ("This response contains TODO items that need to be completed", False),
        ("This is... ", False),  # Incomplete
        ("word " * 100, False),  # Repetitive
    ]
    
    for response, expected in test_cases:
        result, data = guardrail(response)
        status = "✓" if result == expected else "✗"
        print(f"\n{status} Test: {response[:50]}...")
        print(f"  Expected: {expected}, Got: {result}")
        if not result:
            print(f"  Reason: {data}")


def test_safety_guardrail():
    """Test safety guardrail"""
    print("\n\nTesting SafetyGuardrail...")
    
    guardrail = create_safety_guardrail(check_code=True)
    
    test_cases = [
        ("This is a safe response with no sensitive information", True),
        ("My SSN is 123-45-6789", False),
        ("password: mysecret123", False),
        ("rm -rf / # Don't run this!", False),
        ("eval(user_input)", False),
    ]
    
    for response, expected in test_cases:
        result, data = guardrail(response)
        status = "✓" if result == expected else "✗"
        print(f"\n{status} Test: {response[:50]}...")
        print(f"  Expected: {expected}, Got: {result}")
        if not result:
            print(f"  Reason: {data}")


def test_accuracy_guardrail():
    """Test factual accuracy guardrail"""
    print("\n\nTesting FactualAccuracyGuardrail...")
    
    guardrail = create_accuracy_guardrail()
    
    test_cases = [
        ("The Earth revolves around the Sun", True),
        ("2 + 2 = 4", True),
        ("2 + 2 = 5", False),
        ("The Sun revolves around the Earth", False),
        ("Copyright 2030", False),  # Future year
    ]
    
    for response, expected in test_cases:
        result, data = guardrail(response)
        status = "✓" if result == expected else "✗"
        print(f"\n{status} Test: {response[:50]}...")
        print(f"  Expected: {expected}, Got: {result}")
        if not result:
            print(f"  Reason: {data}")


def test_combined_guardrails():
    """Test combining multiple guardrails"""
    print("\n\nTesting Combined Guardrails...")
    
    quality = create_quality_guardrail()
    safety = create_safety_guardrail()
    
    test_response = "This is a comprehensive and safe response that provides detailed information without any sensitive data or dangerous code patterns. It maintains high quality throughout."
    
    print(f"Test response: {test_response[:80]}...")
    
    # Test quality
    q_result, q_data = quality(test_response)
    print(f"\n✓ Quality check: {'PASS' if q_result else 'FAIL'}")
    if not q_result:
        print(f"  Reason: {q_data}")
    
    # Test safety
    s_result, s_data = safety(test_response)
    print(f"✓ Safety check: {'PASS' if s_result else 'FAIL'}")
    if not s_result:
        print(f"  Reason: {s_data}")
    
    print(f"\nOverall: {'✅ PASS' if q_result and s_result else '❌ FAIL'}")


def main():
    """Run all tests"""
    print("=== Guardrail Tests ===\n")
    
    try:
        test_quality_guardrail()
        test_safety_guardrail()
        test_accuracy_guardrail()
        test_combined_guardrails()
        
        print("\n\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()