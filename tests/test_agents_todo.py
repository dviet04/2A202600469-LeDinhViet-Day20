import pytest

from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState


def test_supervisor_routing_decision() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    # Supervisor should make a routing decision and record it in route_history
    state = SupervisorAgent().run(state)
    assert state.route_history, "Supervisor must record a routing decision"
    assert state.route_history[-1] in {"researcher", "analyst", "writer", "done"}
