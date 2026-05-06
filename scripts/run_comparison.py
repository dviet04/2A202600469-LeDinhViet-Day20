from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.evaluation.benchmark import compute_benchmark
from multi_agent_research_lab.evaluation.report import generate_report, generate_comparison_report
from multi_agent_research_lab.observability.tracing import write_trace_file, configure_file_logger
import logging

configure_file_logger(path="logs/run_comparison.log")
logger = logging.getLogger(__name__)

q = "Tóm tắt ngắn về HITL trong AI"

# Run baseline: single LLM call answering the query directly
settings_prompt = "You are a helpful assistant that answers the user's query concisely."
user_prompt = f"Answer the query concisely:\n\n{q}"
client = LLMClient()
try:
    resp = client.complete(system_prompt=settings_prompt, user_prompt=user_prompt)
    baseline_state = ResearchState(request=ResearchQuery(query=q))
    baseline_state.final_answer = resp.content
    baseline_state.agent_results.append(
        # Use minimal AgentResult-like dict since AgentResult import may be heavy
        type("AR", (), {"agent": "baseline", "content": resp.content, "metadata": {"input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens}})()
    )
except Exception as exc:
    logger.exception("Baseline LLM failed: %s", exc)
    baseline_state = ResearchState(request=ResearchQuery(query=q))
    baseline_state.errors.append(str(exc))

# Run multi-agent workflow
wf = MultiAgentWorkflow()
ma_state = wf.run(ResearchState(request=ResearchQuery(query=q)))

# Compute benchmarks
bm_baseline = compute_benchmark(baseline_state)
bm_multi = compute_benchmark(ma_state)

# Generate outputs
generate_report(baseline_state, out_path="reports/baseline_report.md")
generate_report(ma_state, out_path="reports/multi_report.md")
comp = generate_comparison_report(bm_baseline, bm_multi, baseline_name="baseline", multi_name="multi-agent", out_path="reports/comparison.md")
trace_b = write_trace_file(baseline_state, out_path="reports/baseline_trace.json")
trace_m = write_trace_file(ma_state, out_path="reports/multi_trace.json")
logger.info("Wrote baseline=%s multi=%s comparison=%s", trace_b, trace_m, "reports/comparison.md")
print(comp)
