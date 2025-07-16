"""Core components of OKAMI system"""

# Use standard CrewAI classes directly
from crewai import Agent, Task, Crew

# Import managers (these don't extend CrewAI classes)
from .memory_manager import MemoryManager
from .knowledge_manager import KnowledgeManager
from .guardrail_manager import GuardrailManager
from .evolution_tracker import EvolutionTracker

__all__ = [
    "Agent",
    "Task", 
    "Crew",
    "MemoryManager",
    "KnowledgeManager",
    "GuardrailManager",
    "EvolutionTracker",
]