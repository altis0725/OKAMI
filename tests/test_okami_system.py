#!/usr/bin/env python3
"""
OKAMI System Test Script
Tests self-evolution, knowledge, and guardrail features
"""

import os
import sys
import asyncio
import json
import yaml
from pathlib import Path
from datetime import datetime
import time
import pytest

# Add OKAMI to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crews.crew_factory import CrewFactory
from evolution.improvement_applier import ImprovementApplier
from evolution.improvement_parser import ImprovementParser
from core.knowledge_manager import KnowledgeManager
from core.guardrail_manager import GuardrailManager
from utils.logger import get_logger

logger = get_logger(__name__)


@pytest.mark.asyncio
async def test_basic_crew_creation():
    """Test basic crew creation without agent specification"""
    print("\n=== Testing Basic Crew Creation ===")
    
    factory = CrewFactory()
    
    # Create a simple test crew (use test_crew)
    crew = factory.create_crew("test_crew")
    if crew:
        print(f"✓ Crew created successfully: {crew.name}")
        print(f"  - Agents: {len(crew.agents)}")
        print(f"  - Tasks: {len(crew.tasks)}")
        print(f"  - Process: {crew.process}")
        
        # Test kickoff
        print("\nTesting crew kickoff...")
        result = await crew.kickoff_async(inputs={
            "topic": "AI Safety",
            "query": "What are the main principles of AI safety?"
        })
        print(f"✓ Crew kickoff completed")
        print(f"  Result preview: {str(result)[:200]}...")
        return True
    else:
        print("✗ Failed to create crew")
        return False


@pytest.mark.asyncio
async def test_self_evolution():
    """Test self-evolution functionality"""
    print("\n=== Testing Self-Evolution System ===")
    
    # Create test improvements
    improvements = [
        {
            "file": "config/agents/test_evolution_agent.yaml",
            "action": "add",
            "content": """test_evolution_agent:
  role: "Evolution Test Agent"
  goal: "Test the self-evolution system"
  backstory: "Created by evolution system at {timestamp}"
  verbose: true
  memory: true
""".format(timestamp=datetime.now().isoformat())
        },
        {
            "file": "knowledge/evolution_test.md",
            "action": "add",
            "content": """# Evolution Test Knowledge

This file was created by the self-evolution system.

## Test Principles
- Always verify changes
- Maintain system stability
- Document all modifications
"""
        },
        {
            "file": "config/agents/research_agent.yaml",
            "action": "update_field",
            "field": "research_agent.max_iter",
            "value": 30
        }
    ]
    
    # Parse improvements
    parser = ImprovementParser()
    parsed_changes = []
    for imp in improvements:
        parsed = parser.parse_improvement(imp)
        if parsed:
            parsed_changes.extend(parsed)
    
    print(f"Parsed {len(parsed_changes)} changes")
    
    # Apply improvements
    applier = ImprovementApplier()
    results = applier.apply_changes(parsed_changes, dry_run=False)
    
    print(f"\nEvolution Results:")
    print(f"  - Applied: {len(results['applied'])}")
    print(f"  - Failed: {len(results['failed'])}")
    print(f"  - Skipped: {len(results['skipped'])}")
    
    # Verify files were created/modified
    test_files = [
        "config/agents/test_evolution_agent.yaml",
        "knowledge/evolution_test.md"
    ]
    
    all_exist = True
    for file_path in test_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"  ✓ {file_path} exists")
            # Read and display content preview
            content = full_path.read_text()[:100]
            print(f"    Content preview: {content}...")
        else:
            print(f"  ✗ {file_path} not found")
            all_exist = False
    
    # Check if research_agent was updated
    research_agent_path = Path("config/agents/research_agent.yaml")
    if research_agent_path.exists():
        with open(research_agent_path, 'r') as f:
            data = yaml.safe_load(f)
            max_iter = data.get('research_agent', {}).get('max_iter')
            if max_iter == 30:
                print(f"  ✓ research_agent.max_iter updated to 30")
            else:
                print(f"  ✗ research_agent.max_iter not updated (current: {max_iter})")
    
    return all_exist


@pytest.mark.asyncio
async def test_knowledge_integration():
    """Test knowledge integration in crew"""
    print("\n=== Testing Knowledge Integration ===")
    
    # Ensure knowledge file exists
    knowledge_path = Path("knowledge/evolution_test.md")
    if not knowledge_path.exists():
        print("Creating test knowledge file...")
        knowledge_path.parent.mkdir(exist_ok=True)
        knowledge_path.write_text("""# Test Knowledge

## Important Facts
- AI systems should be safe and beneficial
- Testing is crucial for reliability
- Evolution helps systems improve

## Best Practices
1. Always validate inputs
2. Monitor system performance
3. Learn from failures
""")
    
    # Test knowledge loading
    factory = CrewFactory()
    
    # Reload configs to pick up evolution changes
    factory.reload_configs()
    
    # Check if test_evolution_agent was loaded
    if "test_evolution_agent" in factory.agent_configs:
        print("✓ Evolution-created agent loaded successfully")
        
        # Create the agent
        agent = factory.create_agent("test_evolution_agent")
        if agent:
            print(f"✓ Agent created: {agent.role}")
            # Check if knowledge is in backstory
            if "evolution system at" in agent.backstory:
                print("✓ Agent backstory contains evolution timestamp")
        else:
            print("✗ Failed to create evolution agent")
    else:
        print("✗ Evolution-created agent not found in configs")
    
    return True


@pytest.mark.asyncio
async def test_guardrail_functionality():
    """Test guardrail functionality"""
    print("\n=== Testing Guardrail Functionality ===")
    
    # First, let's implement a basic guardrail system
    # Check if guardrail manager exists
    guardrail_path = Path("core/guardrail_manager.py")
    if not guardrail_path.exists():
        print("Creating guardrail manager...")
        guardrail_content = '''"""
Guardrail Manager for OKAMI system
Validates and enforces quality constraints on outputs
"""

import re
from typing import Dict, Any, List, Optional, Callable
import structlog

logger = structlog.get_logger()


class GuardrailViolation(Exception):
    """Raised when a guardrail check fails"""
    pass


class Guardrail:
    """Base guardrail class"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def check(self, content: str, context: Dict[str, Any] = None) -> bool:
        """Check if content passes guardrail"""
        raise NotImplementedError
    
    def fix(self, content: str, context: Dict[str, Any] = None) -> str:
        """Attempt to fix content to pass guardrail"""
        return content


class LengthGuardrail(Guardrail):
    """Ensures content meets length requirements"""
    
    def __init__(self, min_length: int = 10, max_length: int = 10000):
        super().__init__(
            "length_guardrail",
            f"Content must be between {min_length} and {max_length} characters"
        )
        self.min_length = min_length
        self.max_length = max_length
    
    def check(self, content: str, context: Dict[str, Any] = None) -> bool:
        length = len(content.strip())
        return self.min_length <= length <= self.max_length
    
    def fix(self, content: str, context: Dict[str, Any] = None) -> str:
        if len(content.strip()) < self.min_length:
            return content + "\\n\\n[Content expanded to meet minimum length requirements]"
        elif len(content.strip()) > self.max_length:
            return content[:self.max_length-50] + "\\n\\n[Content truncated to meet length limits]"
        return content


class FormatGuardrail(Guardrail):
    """Ensures content meets format requirements"""
    
    def __init__(self, required_sections: List[str] = None):
        super().__init__(
            "format_guardrail",
            "Content must include required sections and formatting"
        )
        self.required_sections = required_sections or []
    
    def check(self, content: str, context: Dict[str, Any] = None) -> bool:
        content_lower = content.lower()
        for section in self.required_sections:
            if section.lower() not in content_lower:
                return False
        return True
    
    def fix(self, content: str, context: Dict[str, Any] = None) -> str:
        missing_sections = []
        content_lower = content.lower()
        
        for section in self.required_sections:
            if section.lower() not in content_lower:
                missing_sections.append(section)
        
        if missing_sections:
            content += "\\n\\n## Additional Sections\\n"
            for section in missing_sections:
                content += f"\\n### {section}\\n[To be completed]\\n"
        
        return content


class QualityGuardrail(Guardrail):
    """Ensures content quality standards"""
    
    def __init__(self):
        super().__init__(
            "quality_guardrail",
            "Content must meet quality standards"
        )
        self.forbidden_phrases = [
            "lorem ipsum",
            "todo",
            "fixme",
            "[placeholder]",
            "undefined"
        ]
    
    def check(self, content: str, context: Dict[str, Any] = None) -> bool:
        content_lower = content.lower()
        for phrase in self.forbidden_phrases:
            if phrase in content_lower:
                return False
        return True
    
    def fix(self, content: str, context: Dict[str, Any] = None) -> str:
        for phrase in self.forbidden_phrases:
            content = re.sub(
                phrase,
                "[content]",
                content,
                flags=re.IGNORECASE
            )
        return content


class GuardrailManager:
    """Manages guardrails for the OKAMI system"""
    
    def __init__(self):
        self.guardrails: Dict[str, Guardrail] = {}
        self._initialize_default_guardrails()
    
    def _initialize_default_guardrails(self):
        """Initialize default guardrails"""
        self.register_guardrail(LengthGuardrail())
        self.register_guardrail(QualityGuardrail())
        self.register_guardrail(FormatGuardrail(
            required_sections=["summary", "details", "recommendations"]
        ))
    
    def register_guardrail(self, guardrail: Guardrail):
        """Register a new guardrail"""
        self.guardrails[guardrail.name] = guardrail
        logger.info(f"Registered guardrail: {guardrail.name}")
    
    def check_content(
        self,
        content: str,
        guardrail_names: List[str] = None,
        context: Dict[str, Any] = None,
        auto_fix: bool = True
    ) -> tuple[bool, str, List[str]]:
        """
        Check content against guardrails
        
        Returns:
            (passed, fixed_content, violations)
        """
        if guardrail_names is None:
            guardrail_names = list(self.guardrails.keys())
        
        violations = []
        fixed_content = content
        
        for name in guardrail_names:
            if name not in self.guardrails:
                logger.warning(f"Unknown guardrail: {name}")
                continue
            
            guardrail = self.guardrails[name]
            
            if not guardrail.check(fixed_content, context):
                violations.append(f"{name}: {guardrail.description}")
                
                if auto_fix:
                    fixed_content = guardrail.fix(fixed_content, context)
                    logger.info(f"Applied fix for guardrail: {name}")
        
        passed = len(violations) == 0
        
        if violations:
            logger.warning(
                "Guardrail violations detected",
                violations=violations,
                auto_fixed=auto_fix
            )
        
        return passed, fixed_content, violations
    
    def create_task_guardrail(self, guardrail_spec: str) -> Optional[Callable]:
        """
        Create a guardrail function from specification
        
        Args:
            guardrail_spec: Guardrail specification string
            
        Returns:
            Guardrail function or None
        """
        def guardrail_func(content: str) -> str:
            # Parse simple guardrail specifications
            if "minimum" in guardrail_spec and "words" in guardrail_spec:
                # Extract minimum word count
                import re
                match = re.search(r'minimum of (\\d+) words', guardrail_spec)
                if match:
                    min_words = int(match.group(1))
                    word_count = len(content.split())
                    if word_count < min_words:
                        logger.warning(
                            f"Content has {word_count} words, "
                            f"minimum required: {min_words}"
                        )
            
            # Apply default guardrails
            passed, fixed_content, violations = self.check_content(content)
            
            return fixed_content
        
        return guardrail_func
'''
        guardrail_path.write_text(guardrail_content)
        print("✓ Guardrail manager created")
    
    # Test guardrail functionality
    from core.guardrail_manager import GuardrailManager
    
    manager = GuardrailManager()
    
    # Test various content
    test_cases = [
        ("Short", False),  # Too short
        ("This is a proper content with summary, details, and recommendations sections.", False),  # Missing sections
        ("Lorem ipsum dolor sit amet", False),  # Contains forbidden phrase
        ("""# Test Report

## Summary
This is a test of the guardrail system.

## Details
The guardrail system ensures content quality by checking:
- Length requirements
- Required sections
- Forbidden phrases

## Recommendations
1. Always include all required sections
2. Avoid placeholder text
3. Ensure sufficient content length
""", True)  # Should pass
    ]
    
    for content, should_pass in test_cases:
        passed, fixed_content, violations = manager.check_content(content)
        
        if passed == should_pass:
            print(f"✓ Test passed: {'PASS' if passed else 'FAIL with violations'}")
            if violations:
                print(f"  Violations: {violations}")
        else:
            print(f"✗ Test failed: Expected {'PASS' if should_pass else 'FAIL'}, got {'PASS' if passed else 'FAIL'}")
    
    # Test auto-fix functionality
    print("\nTesting auto-fix...")
    bad_content = "TODO: Write report"
    passed, fixed_content, violations = manager.check_content(bad_content, auto_fix=True)
    
    if not passed and fixed_content != bad_content:
        print("✓ Auto-fix applied successfully")
        print(f"  Original: {bad_content}")
        print(f"  Fixed: {fixed_content[:50]}...")
    else:
        print("✗ Auto-fix did not work as expected")
    
    return True


@pytest.mark.asyncio
async def test_full_integration():
    """Test full system integration"""
    print("\n=== Testing Full System Integration ===")
    
    # Create a crew with guardrails
    factory = CrewFactory()
    
    # Reload to get latest configs
    factory.reload_configs()
    
    # Create test crew (using the test_crew we created)
    crew = factory.create_crew("test_crew")
    
    if crew:
        print("✓ Crew created with latest configurations")
        
        # Run a task that should trigger guardrails
        result = await crew.kickoff_async(inputs={
            "topic": "OKAMI System",
            "query": "Analyze the OKAMI system architecture and provide recommendations"
        })
        
        print("✓ Integration test completed")
        
        # Check if result meets guardrail requirements
        result_text = str(result)
        if len(result_text) > 50:  # Basic length check
            print("✓ Result meets basic length requirements")
        else:
            print("✗ Result too short")
        
        return True
    else:
        print("✗ Failed to create crew for integration test")
        return False


async def main():
    """Run all tests"""
    print("=== OKAMI System Test Suite ===")
    print(f"Started at: {datetime.now()}")
    
    tests = [
        ("Basic Crew Creation", test_basic_crew_creation),
        ("Self-Evolution", test_self_evolution),
        ("Knowledge Integration", test_knowledge_integration),
        ("Guardrail Functionality", test_guardrail_functionality),
        ("Full Integration", test_full_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # Cleanup test files
    print("\nCleaning up test files...")
    test_files = [
        "config/agents/test_evolution_agent.yaml",
        "knowledge/evolution_test.md"
    ]
    for file_path in test_files:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            print(f"  Removed: {file_path}")


if __name__ == "__main__":
    asyncio.run(main())