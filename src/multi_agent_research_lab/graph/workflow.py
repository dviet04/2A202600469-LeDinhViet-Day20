"""LangGraph workflow skeleton."""

import time
import logging
import datetime
from typing import Callable

from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.core.config import get_settings
from typing import Optional


# Import agents here to avoid circular imports when modules are used standalone
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.observability.tracing import start_timer, stop_timer, record_metric


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def build(self) -> object:
        """Create a LangGraph graph.

        TODO(student): Implement nodes, edges, conditional routing, and stop condition.
        Suggested nodes: supervisor, researcher, analyst, writer, optional critic.
        """

        # Minimal build implementation for the lab: return a simple description
        # In a full implementation this would construct a LangGraph graph object.
        return {
            "nodes": ["supervisor", "researcher", "analyst", "writer"],
            "edges": [("supervisor", "researcher"), ("researcher", "analyst"), ("analyst", "writer")],
        }

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state.

        TODO(student): Compile graph, invoke it, and convert result back to ResearchState.
        """

        # Simple orchestration implementation for the lab starter.
        # Runs in sequence: researcher -> analyst -> writer, using execute_with_retry
        settings = get_settings()

        # Instantiate workers
        researcher = ResearcherAgent()
        analyst = AnalystAgent()
        writer = WriterAgent()

        # Helper to run a worker with retry using the provided executor
        def run_worker(worker_fn, st: ResearchState) -> ResearchState:
            return self.execute_with_retry(worker_fn, st, retry_max=3, fallback_delays=(5, 10, 60))

        # Orchestration loop: supervisor decides which worker to invoke next
        state = state

        # record overall workflow start
        wf_start = start_timer()

        supervisor = SupervisorAgent()
        # Loop until done or max_iterations reached
        for _ in range(settings.max_iterations):
            # Ask supervisor to choose next route
            state = supervisor.run(state)
            next_route = state.route_history[-1] if state.route_history else "researcher"

            if next_route == "researcher":
                state = run_worker(researcher.run, state)
            elif next_route == "analyst":
                state = run_worker(analyst.run, state)
            elif next_route == "writer":
                state = run_worker(writer.run, state)
            elif next_route == "done":
                state.add_trace_event("workflow", {"action": "completed"})
                wf_elapsed = stop_timer(wf_start)
                record_metric(state, "workflow_latency_seconds", wf_elapsed)
                return state
            else:
                # unknown route: surface error and stop
                state.add_trace_event("workflow", {"action": "invalid_route", "route": next_route})
                raise StudentTodoError(f"Supervisor returned unknown route: {next_route}")

        # If loop exits without final_answer, surface helpful error and return state
        state.add_trace_event("workflow", {"action": "incomplete", "reason": "max_iterations_exhausted"})
        wf_elapsed = stop_timer(wf_start)
        record_metric(state, "workflow_latency_seconds", wf_elapsed)
        raise StudentTodoError("MultiAgentWorkflow did not produce a final answer within max_iterations")

    def execute_with_retry(
        self,
        worker_fn: Callable[[ResearchState], ResearchState],
        state: ResearchState,
        retry_max: int = 3,
        fallback_delays: tuple[int, ...] = (5, 10, 60),
    ) -> ResearchState:
        """Execute a worker function with retry and fallback delays.

        Behavior:
        - Try up to `retry_max` times.
        - Between retries, sleep using `fallback_delays` sequence (first 5s, then 10s).
        - If a single attempt exceeds `timeout_seconds` from settings, treat as failure and retry.
        - On final failure, raise `StudentTodoError` and record a trace event.
        """

        settings = get_settings()
        last_exc: Exception | None = None
        logger = logging.getLogger(__name__)

        for attempt in range(1, retry_max + 1):
            attempt_start = time.time()
            started_at = datetime.datetime.utcnow().isoformat() + "Z"
            state.add_trace_event("executor", {"action": "attempt_start", "attempt": attempt, "started_at": started_at})
            try:
                result = worker_fn(state)
                elapsed = time.time() - attempt_start
                # Check timeout guardrail (best-effort; cannot preempt blocking calls)
                if elapsed > settings.timeout_seconds:
                    err = (
                        f"timeout: worker exceeded timeout_seconds={settings.timeout_seconds} (elapsed={elapsed:.2f}s)"
                    )
                    state.add_trace_event("executor", {"action": "timeout", "attempt": attempt, "elapsed": elapsed, "started_at": started_at})
                    last_exc = StudentTodoError(err)
                    raise last_exc

                # success: record elapsed and timestamp
                state.add_trace_event("executor", {"action": "attempt_success", "attempt": attempt, "elapsed": elapsed, "started_at": started_at})
                logger.info("Worker succeeded on attempt %d in %.2fs", attempt, elapsed)
                return result

            except Exception as exc:  # pragma: no cover - runtime failures handled by orchestration
                elapsed = time.time() - attempt_start
                last_exc = exc
                state.errors.append(str(exc))
                state.add_trace_event(
                    "executor",
                    {"action": "attempt_failure", "attempt": attempt, "error": str(exc), "elapsed": elapsed, "started_at": started_at},
                )
                logger.warning("Worker attempt %d failed after %.2fs: %s", attempt, elapsed, exc)

                if attempt < retry_max:
                    # determine delay (use last delay if out of range)
                    delay = fallback_delays[attempt - 1] if attempt - 1 < len(fallback_delays) else fallback_delays[-1]
                    # record retry metric / trace
                    state.add_trace_event("executor", {"action": "executor_retry", "attempt": attempt, "delay": delay, "error": str(exc)})
                    logger.info("Retrying worker after %ds (attempt %d/%d)", delay, attempt, retry_max)
                    state.add_trace_event("executor", {"action": "fallback_sleep", "delay": delay, "attempt": attempt})
                    time.sleep(delay)
                    continue

                # final failure: record and raise with helpful message
                total_elapsed = time.time() - attempt_start
                state.add_trace_event(
                    "executor",
                    {"action": "failure", "reason": "max_retries_exceeded", "attempts": retry_max, "total_elapsed": total_elapsed},
                )
                logger.error("Worker failed after %d attempts: %s", retry_max, last_exc)
                raise StudentTodoError("Hệ thống đang gặp vấnề, vui lòng thử lại sau") from last_exc
