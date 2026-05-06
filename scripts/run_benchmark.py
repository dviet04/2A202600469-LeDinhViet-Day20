from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.evaluation.report import generate_report
from multi_agent_research_lab.observability.tracing import write_trace_file, configure_file_logger
import logging

# configure file logger for this run
configure_file_logger(path="logs/run_benchmark.log")
logger = logging.getLogger(__name__)

q = "Explain the benefits and challenges of multi-agent systems in AI research, and provide examples of real-world applications where they have been successfully implemented."
state = ResearchState(request=ResearchQuery(query=q))
wf = MultiAgentWorkflow()
state = wf.run(state)
report = generate_report(state, out_path="reports/last_report.md")
trace_path = write_trace_file(state, out_path="reports/last_trace.json")
logger.info("Wrote report to reports/last_report.md and trace to %s", trace_path)
print(report)