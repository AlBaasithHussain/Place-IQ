"""Minimal client for OpenAI-compatible Chat Completions APIs.

Works with OpenAI, Azure OpenAI (compatible mode), Groq, Together, OpenRouter,
Ollama and anything else exposing ``POST {base_url}/chat/completions`` with
``response_format`` JSON mode. No vendor SDK is required — just httpx.
"""

import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("app.llm")


class LLMError(Exception):
    """Raised when the LLM service cannot be reached or responds unexpectedly."""


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
    ) -> None:
        parsed = urlparse(base_url)
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or (parsed.scheme == "http" and parsed.hostname not in local_hosts)
        ):
            raise LLMError("LLM_BASE_URL must be HTTPS except for local development hosts")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat request asking for JSON and return the raw content."""
        payload = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("LLM request failed: %s", exc)
            raise LLMError("LLM request failed") from exc

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM returned an unexpected response shape") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMError("LLM returned empty content")
        return content
