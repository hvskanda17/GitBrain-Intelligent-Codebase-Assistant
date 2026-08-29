from collections.abc import AsyncGenerator
from typing import Protocol

from openai import AsyncOpenAI


class LLMClient(Protocol):
    async def generate(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        """Generate a complete completion for the given messages."""
        ...

    async def stream(
        self, messages: list[dict[str, str]], temperature: float = 0.0
    ) -> AsyncGenerator[str, None]:
        """Stream the completion for the given messages."""
        ...


class OpenAILLMClient(LLMClient):
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def generate(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=False,
        )
        return response.choices[0].message.content or ""

    async def stream(
        self, messages: list[dict[str, str]], temperature: float = 0.0
    ) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                yield content


class MockLLMClient(LLMClient):
    """Deterministic mock for tests."""

    def __init__(self, mock_response: str = "mock response") -> None:
        self.mock_response = mock_response

    async def generate(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        return self.mock_response

    async def stream(
        self, messages: list[dict[str, str]], temperature: float = 0.0
    ) -> AsyncGenerator[str, None]:
        # Stream word by word (or token by token) to simulate streaming
        for word in self.mock_response.split(" "):
            yield f"{word} "
