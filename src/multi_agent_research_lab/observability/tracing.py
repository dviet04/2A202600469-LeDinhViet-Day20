"""Simple tracing / metric helpers for the lab.

These helpers record lightweight metrics into `ResearchState.metrics` and
append trace events so the evaluation code can compute benchmarks.
"""
from __future__ import annotations

import time
from typing import Any
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from multi_agent_research_lab.core.state import ResearchState


def start_timer() -> float:
    return time.time()


def stop_timer(start: float) -> float:
    return time.time() - start


def record_metric(state: ResearchState, name: str, value: Any) -> None:
    # store metric and add trace event
    state.metrics[name] = value
    state.add_trace_event("metric", {"name": name, "value": value})


def increment_counter(state: ResearchState, name: str, delta: int = 1) -> None:
    prev = int(state.metrics.get(name, 0) or 0)
    state.metrics[name] = prev + delta
    state.add_trace_event("metric", {"name": name, "value": state.metrics[name]})


def write_trace_file(state: ResearchState, out_path: str | None = None) -> str:
    """Write trace + metrics + errors to a JSON file and return path."""
    if out_path is None:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        out_path = f"reports/trace_{ts}.json"

    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # compute costs before writing trace
    try:
        costs = compute_costs(state)
    except Exception:
        costs = {}

    serializable = {
        "trace": state.trace,
        "metrics": state.metrics,
        "errors": state.errors,
        "final_answer": state.final_answer,
        "iteration": state.iteration,
        "route_history": state.route_history,
    }

    # agent_results may contain pydantic models; convert to dicts if possible
    try:
        serializable["agent_results"] = []
        for r in state.agent_results:
            if hasattr(r, "dict"):
                serializable["agent_results"].append(r.dict())
            elif isinstance(r, dict):
                serializable["agent_results"].append(r)
            elif hasattr(r, "__dict__"):
                # convert simple objects to dict
                serializable["agent_results"].append({k: v for k, v in vars(r).items()})
            else:
                serializable["agent_results"].append(str(r))
    except Exception:
        serializable["agent_results"] = [str(r) for r in state.agent_results]

    # attach cost breakdown if available
    if costs:
        serializable["cost_by_agent"] = costs.get("cost_by_agent")
        serializable["estimated_cost_usd"] = costs.get("estimated_cost_usd")

    with p.open("w", encoding="utf-8") as fh:
        json.dump(serializable, fh, ensure_ascii=False, indent=2)

    return str(p)


def compute_costs(state: ResearchState, input_token_rate: float = 0.000001, output_token_rate: float = 0.000002) -> Dict[str, object]:
    """Estimate costs per agent and total based on token counts in `agent_results`.

    Rates are USD per token (approximate). Returns a dict with `cost_by_agent` and `estimated_cost_usd`.
    """
    cost_by_agent: Dict[str, float] = {}
    total_cost = 0.0

    for r in getattr(state, "agent_results", []):
        agent = getattr(r, "agent", "unknown")
        meta = getattr(r, "metadata", {}) or {}
        input_tokens = int(meta.get("input_tokens") or 0)
        output_tokens = int(meta.get("output_tokens") or 0)
        cost = input_tokens * input_token_rate + output_tokens * output_token_rate
        prev = float(cost_by_agent.get(agent, 0.0) or 0.0)
        cost_by_agent[agent] = prev + cost
        total_cost += cost

    # store in metrics for other consumers
    state.metrics["cost_by_agent"] = cost_by_agent
    state.metrics["estimated_cost_usd"] = total_cost
    state.add_trace_event("metric", {"name": "estimated_cost_usd", "value": total_cost})

    return {"cost_by_agent": cost_by_agent, "estimated_cost_usd": total_cost}


def configure_file_logger(path: str = "logs/app.log", level: int = None) -> None:
    """Add a file handler to the root logger writing to `path`."""
    import logging

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fh = logging.FileHandler(p, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    fh.setFormatter(fmt)
    root = logging.getLogger()
    if level is not None:
        root.setLevel(level)
    root.addHandler(fh)
"""Tracing hooks.

This file intentionally avoids binding to one provider. Students can plug in LangSmith,
Langfuse, OpenTelemetry, or simple JSON traces.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Minimal span context used by the skeleton.

    TODO(student): Replace or augment with LangSmith/Langfuse provider spans.
    """

    started = perf_counter()
    span: dict[str, Any] = {"name": name, "attributes": attributes or {}, "duration_seconds": None}
    try:
        yield span
    finally:
        span["duration_seconds"] = perf_counter() - started
