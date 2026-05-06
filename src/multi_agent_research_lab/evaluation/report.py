"""Generate a human-readable benchmark report from metrics."""
from __future__ import annotations

from typing import Dict
from pathlib import Path

from multi_agent_research_lab.evaluation.benchmark import compute_benchmark
from multi_agent_research_lab.core.state import ResearchState


def generate_report(state: ResearchState, out_path: str | None = None) -> str:
    metrics: Dict[str, object] = compute_benchmark(state)

    lines = []
    lines.append("# Benchmark Report")
    lines.append("")
    lines.append("## Summary Metrics")
    lines.append("")
    lines.append(f"- Latency (s): {metrics['latency_seconds']:.2f}")
    lines.append(f"- Token usage (tokens): {metrics['token_usage']}")
    lines.append(f"- Estimated cost (USD): {metrics.get('estimated_cost_usd', 0.0):.6f}")
    cost_by_agent = metrics.get("cost_by_agent")
    if cost_by_agent:
        lines.append("- Cost by agent:")
        for a, c in cost_by_agent.items():
            lines.append(f"  - {a}: ${c:.6f}")
    # Supervisor summary in top-level metrics
    sup_decisions = metrics.get("supervisor_decisions")
    if sup_decisions is not None:
        lines.append(f"- Supervisor decisions: {sup_decisions}")
    route = metrics.get("route_history")
    if route:
        lines.append(f"- Route history: {', '.join(route)}")
    cov = metrics['citation_coverage']
    lines.append(f"- Citation coverage: {cov if cov is None else f'{cov:.2%}'}")
    lines.append(f"- Failure rate: {metrics['failure_rate']:.2f}")
    lines.append("")
    lines.append("## Notes")
    if state.errors:
        lines.append("- Errors were recorded during execution:")
        for e in state.errors:
            lines.append(f"  - {e}")
    else:
        lines.append("- No runtime errors recorded.")

    # Supervisor summary: route history and decisions
    lines.append("")
    lines.append("## Supervisor")
    lines.append("")
    if getattr(state, "route_history", None):
        lines.append(f"- Route history: {', '.join(state.route_history)}")
        # include detailed supervisor trace events if present
        sup_events = [t for t in state.trace if t.get("name") == "supervisor"]
        if sup_events:
            lines.append("- Supervisor decisions:")
            for ev in sup_events:
                p = ev.get("payload", {})
                it = p.get("iteration")
                nxt = p.get("next")
                guard = p.get("guardrails") or {}
                lines.append(f"  - Iteration {it}: {nxt} (guardrails: max_iterations={guard.get('max_iterations')}, timeout_seconds={guard.get('timeout_seconds')})")
    else:
        lines.append("- No supervisor routing recorded.")

    report = "\n".join(lines)

    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(report, encoding="utf-8")

    return report
"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to markdown.

    TODO(student): Add richer analysis, examples, screenshots, and trace links.
    """

    lines = ["# Benchmark Report", "", "| Run | Latency (s) | Cost (USD) | Quality | Notes |", "|---|---:|---:|---:|---|"]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        lines.append(f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} | {item.notes} |")
    return "\n".join(lines) + "\n"


def generate_comparison_report(baseline_metrics: dict, multi_metrics: dict, baseline_name: str = "baseline", multi_name: str = "multi-agent", out_path: str | None = None) -> str:
    """Generate a markdown comparison between baseline and multi-agent runs.

    Expects the dicts produced by `compute_benchmark()`.
    """
    def fmt_cost(v):
        return f"${v:.6f}" if v is not None else "-"

    lines = ["# Comparison: Baseline vs Multi-Agent", ""]
    lines.append("| Metric | " + baseline_name + " | " + multi_name + " | Delta |")
    lines.append("|---|---:|---:|---:|")

    # Latency
    b_lat = baseline_metrics.get("latency_seconds", 0.0)
    m_lat = multi_metrics.get("latency_seconds", 0.0)
    delta_lat = m_lat - b_lat
    lines.append(f"| Latency (s) | {b_lat:.2f} | {m_lat:.2f} | {delta_lat:+.2f} |")

    # Token usage
    b_tok = baseline_metrics.get("token_usage", 0)
    m_tok = multi_metrics.get("token_usage", 0)
    delta_tok = m_tok - b_tok
    lines.append(f"| Token usage | {b_tok} | {m_tok} | {delta_tok:+} |")

    # Cost
    b_cost = baseline_metrics.get("estimated_cost_usd", 0.0)
    m_cost = multi_metrics.get("estimated_cost_usd", 0.0)
    delta_cost = m_cost - b_cost
    lines.append(f"| Estimated cost (USD) | {fmt_cost(b_cost)} | {fmt_cost(m_cost)} | {fmt_cost(delta_cost)} |")

    # Failure rate
    b_fail = baseline_metrics.get("failure_rate", 0.0)
    m_fail = multi_metrics.get("failure_rate", 0.0)
    delta_fail = m_fail - b_fail
    lines.append(f"| Failure rate | {b_fail:.2f} | {m_fail:.2f} | {delta_fail:+.2f} |")

    # Citation coverage
    b_cov = baseline_metrics.get("citation_coverage")
    m_cov = multi_metrics.get("citation_coverage")
    lines.append(f"| Citation coverage | {b_cov if b_cov is None else f'{b_cov:.2%}'} | {m_cov if m_cov is None else f'{m_cov:.2%}'} | - |")

    # Supervisor decisions (only for multi-agent)
    lines.append(f"| Supervisor decisions | - | {multi_metrics.get('supervisor_decisions', '-') } | - |")

    out = "\n".join(lines) + "\n"
    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out, encoding="utf-8")
    return out
