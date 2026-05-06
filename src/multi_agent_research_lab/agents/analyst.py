"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.core.config import get_settings
import logging
from multi_agent_research_lab.core.schemas import AgentName, AgentResult


client = LLMClient()
logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.

        TODO(student): Extract key claims, compare viewpoints, and flag weak evidence.
        """
        settings = get_settings()

        if not state.research_notes:
            raise StudentTodoError("Analyst requires research_notes to produce analysis")

        system_prompt = "You are an analyst agent: extract key claims, rate evidence strength, and suggest contradictions or gaps. Output a structured analysis and a brief summary."
        user_prompt = (
            "Research notes:\n" + state.research_notes + "\n\n"
            "Instructions: List main claims, supporting sources (if any), confidence score 0-1, and a 2-3 sentence summary of implications."
        )

        try:
            resp = client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            content = resp.content or ""
        except Exception as exc:  # pragma: no cover - runtime
            logger.exception("Analyst LLM failed: %s", exc)
            state.errors.append(str(exc))
            state.add_trace_event("analyst", {"action": "llm_failed", "error": str(exc)})
            if settings.app_env == "local":
                content = "[MOCK ANALYSIS] Could not run LLM; returning mock analysis."
            else:
                raise StudentTodoError(f"Analyst failed: {exc}") from exc

        state.analysis_notes = content
        state.agent_results.append(
            AgentResult(agent=AgentName.ANALYST, content=content, metadata={"input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens})
        )

        state.add_trace_event("analyst", {"action": "completed", "summary_len": len(content)})
        return state
