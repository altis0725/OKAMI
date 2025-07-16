"""
Test main_crew configuration and execution
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crews import CrewFactory
from utils.logger import initialize_logger
import structlog

# Initialize logging
logger = initialize_logger()
test_logger = structlog.get_logger(__name__)


def test_main_crew_loading():
    """Test that main_crew can be loaded properly"""
    test_logger.info("Testing main_crew loading...")
    
    # Create crew factory
    factory = CrewFactory()
    
    # List available crews
    crews = factory.list_crews()
    test_logger.info(f"Available crews", crews=crews)
    
    # Check that main_crew is available
    assert "main_crew" in crews, "main_crew not found in available crews"
    
    # Try to create main_crew
    crew = factory.create_crew("main_crew")
    assert crew is not None, "Failed to create main_crew"
    
    # Check crew properties
    test_logger.info(
        "main_crew created successfully",
        name=crew.name,
        agents=len(crew.agents),
        tasks=len(crew.tasks),
        process=str(crew.process)
    )
    
    # Verify hierarchical process
    assert str(crew.process) == "Process.hierarchical", "main_crew should use hierarchical process"
    
    # Verify manager agent
    assert any(agent.role == "Project Manager" for agent in crew.agents), "Manager agent not found"
    
    # Verify task exists
    assert len(crew.tasks) > 0, "No tasks defined for main_crew"
    
    test_logger.info("✓ main_crew configuration is valid")


def test_crew_execution():
    """Test basic crew execution"""
    test_logger.info("Testing main_crew execution...")
    
    factory = CrewFactory()
    crew = factory.get_crew("main_crew")
    
    if not crew:
        test_logger.error("Failed to get main_crew")
        return
    
    # Test input
    test_input = {
        "task": "Create a simple hello world message"
    }
    
    try:
        # Execute crew
        test_logger.info("Executing crew with test input", input=test_input)
        result = crew.kickoff(inputs=test_input)
        
        test_logger.info(
            "Crew execution completed",
            result_type=type(result),
            result_length=len(str(result)) if result else 0
        )
        
        # Basic validation
        assert result is not None, "Crew returned None result"
        assert len(str(result)) > 0, "Crew returned empty result"
        
        test_logger.info("✓ main_crew execution successful")
        
    except Exception as e:
        test_logger.error("Crew execution failed", error=str(e), exc_info=e)
        raise


def main():
    """Run all tests"""
    test_logger.info("Starting crew tests...")
    
    try:
        # Test loading
        test_main_crew_loading()
        
        # Test execution (optional - requires API keys)
        if os.getenv("OPENAI_API_KEY"):
            test_crew_execution()
        else:
            test_logger.warning("Skipping execution test - no API key found")
        
        test_logger.info("✅ All tests passed!")
        
    except Exception as e:
        test_logger.error("❌ Test failed", error=str(e), exc_info=e)
        sys.exit(1)


if __name__ == "__main__":
    main()