"""Supervisor / router skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.core.config import get_settings
import time
import logging

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route.

        TODO(student): Implement routing policy. Suggested steps:
        - Inspect request, current notes, and missing fields.
        - Choose one of: researcher, analyst, writer, done.
        - Enforce max iterations and failure fallback.
        """

        settings = get_settings()

        # Validation: ensure request is present
        if not state.request or not getattr(state.request, "query", None):
            msg = "Invalid request: empty query provided to Supervisor"
            state.errors.append(msg)
            state.add_trace_event("supervisor", {"action": "validation_failed", "reason": msg})
            raise StudentTodoError(msg)

        # Guardrail: max iterations
        if state.iteration >= settings.max_iterations:
            reason = "max_iterations_reached"
            state.add_trace_event("supervisor", {"action": "stop", "reason": reason, "iteration": state.iteration})
            # make final_answer explicit to avoid silent stops
            if not state.final_answer:
                state.final_answer = f"Stopped after {state.iteration} iterations (max_iterations={settings.max_iterations})."
            return state

        # Simple routing policy based on missing outputs
        if not state.research_notes:
            next_route = "researcher"
        elif not state.analysis_notes:
            next_route = "analyst"
        elif not state.final_answer:
            next_route = "writer"
        else:
            next_route = "done"

        # Record routing decision and guardrail metadata
        state.record_route(next_route)
        state.add_trace_event("supervisor", {
            "action": "route",
            "next": next_route,
            "iteration": state.iteration,
            "guardrails": {
                "max_iterations": settings.max_iterations,
                "timeout_seconds": settings.timeout_seconds,
                "retry_max": 4,
                "fallback_delays_s": [5, 10, 60],
            },
        })

        logger.debug("Supervisor routed to %s (iteration=%d)", next_route, state.iteration)

        return state
