"""Writer agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.core.config import get_settings
import logging
from multi_agent_research_lab.core.schemas import AgentName, AgentResult


client = LLMClient()
logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`.

        TODO(student): Synthesize a clear response with citations or source references.
        """
        # Guardrail: writer must not perform new research or call external search
        if not state.research_notes and not state.sources:
            raise StudentTodoError("Writer requires research notes or sources to produce an answer")

        system_prompt = (
            "You are a writer agent that produces a concise, well-structured final answer for the user. "
            "Do NOT perform new research or invent sources. Cite only from the provided sources or analysis."
        )

        user_parts = []
        if state.analysis_notes:
            user_parts.append("Analysis:\n" + state.analysis_notes)
        if state.research_notes:
            user_parts.append("Research notes:\n" + state.research_notes)
        user_prompt = "\n\n".join(user_parts) + "\n\nInstructions: Write a clear answer targeted to the audience and include inline citations referencing provided sources when appropriate. Keep answer under 500 words."

        settings = get_settings()

        try:
            resp = client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            content = resp.content or ""
        except Exception as exc:  # pragma: no cover - runtime
            logger.exception("Writer LLM failed: %s", exc)
            state.errors.append(str(exc))
            state.add_trace_event("writer", {"action": "llm_failed", "error": str(exc)})
            if settings.app_env == "local":
                content = "[MOCK ANSWER] LLM unavailable; returning mock final answer."
            else:
                raise StudentTodoError(f"Writer failed: {exc}") from exc

        state.final_answer = content
        state.agent_results.append(
            AgentResult(agent=AgentName.WRITER, content=content, metadata={"input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens})
        )

        state.add_trace_event("writer", {"action": "completed", "answer_len": len(content)})
        return state
