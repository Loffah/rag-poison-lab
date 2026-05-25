"""LLM client adapter. Uniform interface over Anthropic, OpenAI-compatible, and
Ollama backends.

Backend selection is driven by env vars. Set one of:

    ANTHROPIC_API_KEY            -> use Anthropic (default model: claude-opus-4-7)
    OPENAI_API_KEY               -> use OpenAI (default model: gpt-4o)

Override the default model per provider with:

    ANTHROPIC_MODEL=claude-sonnet-4-6
    OPENAI_MODEL=gpt-4o-mini

For Azure OpenAI or any OpenAI-compatible endpoint (vLLM, LM Studio,
LiteLLM proxy, internal corporate gateway), set:

    OPENAI_BASE_URL=https://your-endpoint.example/v1

Force a specific backend regardless of env keys with:

    RAG_POISON_LAB_BACKEND=anthropic|openai|ollama

Without any API key, the adapter falls back to a local Ollama instance at
http://localhost:11434 so reviewers can evaluate the tool with zero spend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol

import httpx


class LLMClient(Protocol):
    def generate(self, system: str, user: str) -> str: ...


def _env_default(key: str, fallback: str) -> str:
    return os.environ.get(key, fallback)


def _detect_openai_base_url() -> str | None:
    """If OPENAI_BASE_URL is set, use it. Otherwise infer from the key prefix:
    a 'gsk_*' key is a Groq key and should route to Groq's OpenAI-compatible
    endpoint rather than api.openai.com (which would 401 with a confusing
    message). Returns None for non-Groq OpenAI keys so the SDK uses its
    default api.openai.com.
    """
    explicit = os.environ.get("OPENAI_BASE_URL")
    if explicit:
        return explicit
    key = os.environ.get("OPENAI_API_KEY", "")
    if key.startswith("gsk_"):
        return "https://api.groq.com/openai/v1"
    return None


def _detect_openai_model() -> str:
    """If OPENAI_MODEL is set, use it. Otherwise pick a sensible default for
    the detected provider: a Groq key gets a llama default since gpt-4o
    does not exist on Groq."""
    explicit = os.environ.get("OPENAI_MODEL")
    if explicit:
        return explicit
    key = os.environ.get("OPENAI_API_KEY", "")
    if key.startswith("gsk_"):
        return "llama-3.3-70b-versatile"
    return "gpt-4o"


@dataclass
class AnthropicClient:
    model: str = field(default_factory=lambda: _env_default("ANTHROPIC_MODEL", "claude-opus-4-7"))
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
class OpenAIClient:
    model: str = field(default_factory=_detect_openai_model)
    base_url: str | None = field(default_factory=_detect_openai_base_url)
    max_tokens: int = 1024

    def generate(self, system: str, user: str) -> str:
        from openai import OpenAI

        kwargs: dict = {}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = OpenAI(**kwargs)
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


@dataclass
class OllamaClient:
    model: str = field(default_factory=lambda: _env_default("OLLAMA_MODEL", "llama3.1"))
    host: str = field(default_factory=lambda: _env_default("OLLAMA_HOST", "http://localhost:11434"))

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
    """Pick a client based on environment.

    Explicit override via RAG_POISON_LAB_BACKEND=anthropic|openai|ollama wins.
    Otherwise the first matching API key in (Anthropic, OpenAI) wins.
    Otherwise fall back to a local Ollama instance.
    """
    forced = os.environ.get("RAG_POISON_LAB_BACKEND", "").lower()
    if forced == "anthropic":
        return AnthropicClient()
    if forced == "openai":
        return OpenAIClient()
    if forced == "ollama":
        return OllamaClient()

    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIClient()
    return OllamaClient()
