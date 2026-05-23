"""LLM client adapter — uniform interface over Anthropic and Ollama backends.

Anthropic is the default; Ollama exists so reviewers can evaluate this tool
without paying for API calls. The interface is deliberately narrow: a single
`generate(system, user)` call that returns a string.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx


class LLMClient(Protocol):
    def generate(self, system: str, user: str) -> str: ...


@dataclass
class AnthropicClient:
    model: str = "claude-opus-4-7"
    max_tokens: int = 1024

    def generate(self, system: str, user: str) -> str:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


@dataclass
class OllamaClient:
    model: str = "llama3.1"
    host: str = "http://localhost:11434"

    def generate(self, system: str, user: str) -> str:
        response = httpx.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


def default_client() -> LLMClient:
    """Pick a client from environment. Anthropic if API key set, else Ollama."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    return OllamaClient()
