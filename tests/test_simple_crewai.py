"""
Test basic CrewAI functionality
"""
from crewai import Agent, Task, Crew

# Create a simple agent
agent = Agent(
    role="Researcher",
    goal="Research information",
    backstory="You are a research agent",
    verbose=True
)

print(f"Agent created: {agent.role}")
print(f"Agent class: {agent.__class__}")
print(f"Agent dict: {agent.__dict__}")

# Create a simple task
task = Task(
    description="Research AI trends",
    expected_output="A summary of AI trends",
    agent=agent
)

print(f"\nTask created: {task.description}")
print(f"Task class: {task.__class__}")

# Create a simple crew
crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True
)

print(f"\nCrew created with {len(crew.agents)} agents and {len(crew.tasks)} tasks")
print(f"Crew class: {crew.__class__}")