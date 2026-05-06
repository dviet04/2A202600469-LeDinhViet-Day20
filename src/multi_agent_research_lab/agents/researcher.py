"""Researcher agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient
from multi_agent_research_lab.core.config import get_settings
import logging
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.schemas import SourceDocument


client = LLMClient()
searcher = SearchClient()
logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`.

        TODO(student): Implement search, source filtering, citation capture, and notes.
        """
        if not state.request or not state.request.query:
            raise StudentTodoError("Researcher requires a non-empty query")

        system_prompt = "You are a researcher agent that finds sources and writes concise research notes. Return factual source snippets and a short summary. Respond in plain text; prefer JSON list of sources when possible."
        user_prompt = (
            f"Query: {state.request.query}\nMax sources: {state.request.max_sources}\n"
            "Instructions: Return up to max_sources sources with title, url (if available), and a short snippet. Then provide concise research notes summarizing findings."
        )

        settings = get_settings()

        # First perform a structured search using Serper (or configured search client)
        try:
            sources = searcher.search(state.request.query, max_results=state.request.max_sources)
            state.sources = sources
        except Exception as exc:  # pragma: no cover - network/runtime
            logger.exception("Researcher search failed: %s", exc)
            state.errors.append(str(exc))
            state.add_trace_event("researcher", {"action": "search_failed", "error": str(exc)})
            if settings.app_env == "local":
                sources = [
                    SourceDocument(title="Mock result", url=None, snippet=f"Mock snippet for: {state.request.query}")
                ]
                state.sources = sources
            else:
                raise StudentTodoError(f"Research search failed: {exc}") from exc

        # Summarize found sources using LLM to create concise research_notes
        combined = "\n\n".join([f"Title: {s.title}\nSnippet: {s.snippet}\nURL: {s.url or ''}" for s in state.sources])
        user_prompt = f"Summarize the following sources into concise research notes:\n\n{combined}"
        try:
            resp = client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            content = resp.content or ""
        except Exception as exc:  # pragma: no cover - runtime
            logger.exception("Researcher LLM summarization failed: %s", exc)
            state.errors.append(str(exc))
            state.add_trace_event("researcher", {"action": "summarize_failed", "error": str(exc)})
            if settings.app_env == "local":
                content = "[MOCK SUMMARY] Research notes unavailable; using mock summary."
            else:
                raise StudentTodoError(f"Researcher summarization failed: {exc}") from exc

        state.research_notes = content

        # Record agent result (append AgentResult instance)
        state.agent_results.append(
            AgentResult(agent=AgentName.RESEARCHER, content=content, metadata={"input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens})
        )

        state.add_trace_event("researcher", {"action": "completed", "summary_len": len(content), "num_sources": len(sources)})
        return state
