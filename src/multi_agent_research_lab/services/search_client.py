"""Search client abstraction for ResearcherAgent.

This implementation includes a simple Serper-backed search when `SERPER_API_KEY`
is present in settings. The Serper (google.serper.dev) JSON response returns
`organic` results with `title`, `link`, and `snippet` fields which we map to
the local `SourceDocument` schema.

If no `SERPER_API_KEY` is configured, the client raises a helpful
`StudentTodoError` prompting the student to configure a search provider.
"""

from typing import List

import requests
import logging

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Provider-agnostic search client. Uses Serper when configured."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def search(self, query: str, max_results: int = 5) -> List[SourceDocument]:
        """Return a list of `SourceDocument` for `query`.

        This function currently calls Serper's REST endpoint. The exact
        endpoint and response format may differ; adjust parsing as needed for
        your provider.
        """

        if not self.settings.serper_api_key:
            raise StudentTodoError(
                "SERPER_API_KEY is not set. Configure Serper or implement another search client."
            )

        # Serper public endpoint (google.serper.dev). Uses X-API-KEY header.
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": f"{self.settings.serper_api_key}", "Content-Type": "application/json"}
        payload = {"q": query, "num": max_results}

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # pragma: no cover - network/runtime
            # If running locally, fall back to a small mocked result so the
            # lab flow can be tested offline. In other environments, surface
            # the error to the caller.
            logging.warning("Serper search failed: %s", exc)
            if self.settings.app_env == "local":
                mocked = [
                    SourceDocument(
                        title="Mock result 1",
                        url=None,
                        snippet=f"Mock snippet for query: {query}",
                        metadata={"mock": True},
                    )
                ]
                return mocked
            raise StudentTodoError(f"Serper search failed: {exc}") from exc

        results = []
        # Serper returns `organic` entries for organic results.
        for item in data.get("organic", [])[:max_results]:
            title = item.get("title") or ""
            url_ = item.get("link") or item.get("url")
            snippet = item.get("snippet") or item.get("summary") or ""
            results.append(SourceDocument(title=title, url=url_, snippet=snippet, metadata=item))

        return results
