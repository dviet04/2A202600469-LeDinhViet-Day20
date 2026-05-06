"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass
import time
from typing import Any

import tenacity

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError


try:
    import openai
except Exception:  # pragma: no cover - optional dependency
    openai = None


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client skeleton."""

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion.

        TODO(student): Connect OpenAI, Azure OpenAI, or another provider.
        Keep retry, timeout, and token logging here rather than inside agents.
        """

        settings = get_settings()

        # Prefer OpenAI if API key is available
        if settings.openai_api_key and openai is not None:
            openai.api_key = settings.openai_api_key

            @tenacity.retry(
                stop=tenacity.stop_after_attempt(3),
                wait=tenacity.wait_exponential(multiplier=0.5, min=0.5, max=4),
                reraise=True,
            )
            def _call() -> Any:
                start = time.time()

                # Support new `openai` v1+ interface (OpenAI client) if available
                try:
                    if hasattr(openai, "OpenAI"):
                        client = openai.OpenAI(api_key=settings.openai_api_key)
                        resp = client.chat.completions.create(
                            model=settings.openai_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.0,
                        )
                    else:
                        # Fallback to legacy API
                        resp = openai.ChatCompletion.create(
                            model=settings.openai_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.0,
                        )
                finally:
                    elapsed = time.time() - start

                return resp, elapsed

            try:
                resp, elapsed = _call()
            except Exception as exc:  # pragma: no cover - runtime provider error
                raise StudentTodoError(f"OpenAI call failed: {exc}") from exc

            # Extract content and usage if available (handle both legacy and new client)
            content = ""
            input_tokens = None
            output_tokens = None
            try:
                # Try mapping-style access first
                if isinstance(resp, dict):
                    choices = resp.get("choices", [])
                    if choices:
                        # new-format message object
                        msg = choices[0].get("message") or choices[0]
                        content = msg.get("content") or ""
                    usage = resp.get("usage") or {}
                    input_tokens = usage.get("prompt_tokens")
                    output_tokens = usage.get("completion_tokens")
                else:
                    # Try attribute-style (OpenAI client returns object with .choices and .usage)
                    choices = getattr(resp, "choices", None)
                    if choices:
                        first = choices[0]
                        msg = getattr(first, "message", None) or first
                        content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else "")
                    usage = getattr(resp, "usage", None)
                    if usage:
                        input_tokens = getattr(usage, "prompt_tokens", None) or (usage.get("prompt_tokens") if isinstance(usage, dict) else None)
                        output_tokens = getattr(usage, "completion_tokens", None) or (usage.get("completion_tokens") if isinstance(usage, dict) else None)
            except Exception:
                content = str(resp)

            return LLMResponse(content=content, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=None)

        # If no provider configured, raise helpful error
        raise StudentTodoError(
            "No LLM provider configured. Set OPENAI_API_KEY in .env or implement another provider."
        )
