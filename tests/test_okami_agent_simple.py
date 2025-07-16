"""
Test simplified OkamiAgent
"""
from crewai import Agent
from typing import List, Dict, Any

class SimpleOkamiAgent(Agent):
    """Simplified OKAMI Agent for testing"""
    
    def __init__(self, **kwargs):
        # Call parent init first
        super().__init__(**kwargs)
        
        # Then add custom attributes
        self.execution_history: List[Dict[str, Any]] = []
        self.learning_insights: List[Dict[str, Any]] = []
        
        print(f"SimpleOkamiAgent initialized for role: {self.role}")


# Test creation
try:
    agent = SimpleOkamiAgent(
        role="Test Agent",
        goal="Test goal",
        backstory="Test backstory",
        verbose=True
    )
    print("✓ SimpleOkamiAgent created successfully")
    print(f"  - Has execution_history: {hasattr(agent, 'execution_history')}")
    print(f"  - Has learning_insights: {hasattr(agent, 'learning_insights')}")
except Exception as e:
    print(f"✗ Failed to create SimpleOkamiAgent: {e}")