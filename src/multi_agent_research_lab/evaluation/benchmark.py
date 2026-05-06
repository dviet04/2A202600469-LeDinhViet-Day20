"""Compute benchmark metrics from a completed ResearchState."""
from __future__ import annotations

from typing import Dict

from multi_agent_research_lab.core.state import ResearchState


def compute_benchmark(state: ResearchState) -> Dict[str, object]:
    # Latency: prefer recorded workflow latency metric
    latency = state.metrics.get("workflow_latency_seconds")
    if latency is None:
        # fallback: sum executor elapsed fields from trace
        latency = 0.0
        for t in state.trace:
            p = t.get("payload", {})
            if p.get("action") in ("attempt_success", "attempt_failure") and isinstance(p.get("elapsed"), (int, float)):
                latency += float(p.get("elapsed"))

    # Token usage: sum input+output tokens if available in agent_results metadata
    token_usage = 0
    cost_by_agent = {}
    estimated_cost = 0.0
    for r in getattr(state, "agent_results", []):
        meta = getattr(r, "metadata", {}) or {}
        input_tokens = meta.get("input_tokens") or 0
        output_tokens = meta.get("output_tokens") or 0
        token_usage += int(input_tokens or 0) + int(output_tokens or 0)
        agent = getattr(r, "agent", str(getattr(r, "agent", "unknown")))
        in_t = int(input_tokens or 0)
        out_t = int(output_tokens or 0)
        # simple cost model: USD per token
        INPUT_RATE = 0.000001
        OUTPUT_RATE = 0.000002
        cost = in_t * INPUT_RATE + out_t * OUTPUT_RATE
        prev = float(cost_by_agent.get(agent, 0.0) or 0.0)
        cost_by_agent[agent] = prev + cost
        estimated_cost += cost

    # Citation coverage: proportion of sources that have a URL
    total_sources = len(getattr(state, "sources", []) or [])
    covered = 0
    if total_sources:
        for s in state.sources:
            if getattr(s, "url", None):
                covered += 1
        citation_coverage = covered / total_sources
    else:
        citation_coverage = None

    # Failure rate: 1.0 if there were errors recorded, else 0.0
    failure_rate = 1.0 if state.errors else 0.0

    # Supervisor metrics: number of routing decisions and route history
    supervisor_decisions = 0
    route_history = []
    if getattr(state, "route_history", None):
        route_history = list(state.route_history)
        supervisor_decisions = len(route_history)

    # Include a small estimated cost for supervisor decisions (controller overhead)
    SUPERVISOR_COST_PER_DECISION = 0.000005  # USD per routing decision (heuristic)
    if supervisor_decisions:
        sup_cost = supervisor_decisions * SUPERVISOR_COST_PER_DECISION
        prev = float(cost_by_agent.get("supervisor", 0.0) or 0.0)
        cost_by_agent["supervisor"] = prev + sup_cost
        estimated_cost += sup_cost

    return {
        "latency_seconds": float(latency or 0.0),
        "token_usage": int(token_usage),
        "citation_coverage": citation_coverage,
        "failure_rate": float(failure_rate),
        "estimated_cost_usd": float(estimated_cost),
        "cost_by_agent": cost_by_agent,
        "supervisor_decisions": supervisor_decisions,
        "route_history": route_history,
    }
"""Benchmark skeleton for single-agent vs multi-agent."""

from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState


Runner = Callable[[str], ResearchState]


def run_benchmark(run_name: str, query: str, runner: Runner) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency and return a placeholder metric object.

    TODO(student): Add quality scoring, estimated token cost, citation coverage, and error rate.
    """

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    metrics = BenchmarkMetrics(run_name=run_name, latency_seconds=latency)
    return state, metrics
