"""
Test agent with composition instead of inheritance
"""
from crewai import Agent
from typing import List, Dict, Any

class OkamiAgentWrapper:
    """Wrapper for CrewAI Agent with additional OKAMI features"""
    
    def __init__(self, **agent_kwargs):
        # Create the underlying CrewAI agent
        self.agent = Agent(**agent_kwargs)
        
        # Add OKAMI-specific attributes
        self.execution_history: List[Dict[str, Any]] = []
        self.learning_insights: List[Dict[str, Any]] = []
        
        print(f"OkamiAgentWrapper initialized for role: {self.agent.role}")
    
    # Delegate attribute access to the underlying agent
    def __getattr__(self, name):
        return getattr(self.agent, name)


# Test creation
try:
    wrapper = OkamiAgentWrapper(
        role="Test Agent",
        goal="Test goal", 
        backstory="Test backstory",
        verbose=True
    )
    print("✓ OkamiAgentWrapper created successfully")
    print(f"  - Has execution_history: {hasattr(wrapper, 'execution_history')}")
    print(f"  - Has learning_insights: {hasattr(wrapper, 'learning_insights')}")
    print(f"  - Can access role: {wrapper.role}")
    print(f"  - Underlying agent type: {type(wrapper.agent)}")
except Exception as e:
    print(f"✗ Failed to create OkamiAgentWrapper: {e}")