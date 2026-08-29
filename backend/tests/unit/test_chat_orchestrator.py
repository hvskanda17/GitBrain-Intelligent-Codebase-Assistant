from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import ConfigurationError
from app.llm.llm_client import MockLLMClient
from app.retrieval.context_builder import RetrievedChunk
from app.services.chat_orchestrator import ChatOrchestrator, build_prompt


def test_build_prompt_without_context():
    question = "How does this work?"
    messages = build_prompt(question, [])
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "You are a code-intelligence assistant" in messages[0]["content"]
    assert "Context:" not in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == question


def test_build_prompt_with_context():
    question = "How does this work?"
    chunks = [
        RetrievedChunk(
            source_type="function",
            source_id="123",
            label="function main",
            file_path="main.py",
            chunk_text="def main(): pass",
            score=0.9,
        )
    ]
    messages = build_prompt(question, chunks)
    assert len(messages) == 2
    system_content = messages[0]["content"]
    assert "Context:" in system_content
    assert "--- FUNCTION: function main (File: main.py) ---" in system_content
    assert "def main(): pass" in system_content


@pytest.mark.asyncio
async def test_stream_chat_missing_llm_client():
    chat_service = AsyncMock()
    retrieval_service = AsyncMock()
    orchestrator = ChatOrchestrator(
        chat_service=chat_service,
        retrieval_service=retrieval_service,
        llm_client=None,
    )

    with pytest.raises(ConfigurationError):
        # We must iterate the generator for it to raise the exception synchronously inside
        async for _ in orchestrator.stream_chat(uuid4(), uuid4(), "hello"):
            pass


@pytest.mark.asyncio
async def test_stream_chat_successful():
    session_id = uuid4()
    user_id = uuid4()
    repository_id = uuid4()

    chat_service = AsyncMock()
    # Mock get_session to return a session with our repository_id
    mock_session = AsyncMock()
    mock_session.repository_id = repository_id
    chat_service.get_session.return_value = mock_session

    retrieval_service = AsyncMock()
    # Return one mock chunk
    mock_chunk = RetrievedChunk(
        source_type="function",
        source_id="123",
        label="func",
        file_path="foo.py",
        chunk_text="def foo(): pass",
        score=0.8,
    )
    retrieval_service.retrieve.return_value = [mock_chunk]

    llm_client = MockLLMClient(mock_response="Here is the answer")

    orchestrator = ChatOrchestrator(
        chat_service=chat_service,
        retrieval_service=retrieval_service,
        llm_client=llm_client,
    )

    # Consume the stream
    chunks = []
    async for chunk in orchestrator.stream_chat(session_id, user_id, "how do I use foo?"):
        chunks.append(chunk)

    # Validate output events
    assert len(chunks) > 1
    assert "data: {\"done\": true}" in chunks[-1]
    
    # 1. Validation was called
    chat_service.get_session.assert_called_once_with(session_id, user_id)

    # 2. User message persisted
    assert chat_service.add_message.call_count == 2
    user_call = chat_service.add_message.mock_calls[0]
    assert user_call.kwargs["role"] == "user"
    assert user_call.kwargs["content"] == "how do I use foo?"

    # 3. Retrieval was called
    retrieval_service.retrieve.assert_called_once_with(
        repository_id=repository_id,
        question="how do I use foo?",
    )

    # 4. Assistant message persisted with sources
    assistant_call = chat_service.add_message.mock_calls[1]
    assert assistant_call.kwargs["role"] == "assistant"
    assert "Here " in assistant_call.kwargs["content"]
    assert len(assistant_call.kwargs["sources"]) == 1
    source_meta = assistant_call.kwargs["sources"][0]
    assert source_meta["source_id"] == "123"
    assert source_meta["score"] == 0.8


@pytest.mark.asyncio
async def test_stream_chat_llm_failure():
    session_id = uuid4()
    user_id = uuid4()

    chat_service = AsyncMock()
    chat_service.get_session.return_value = AsyncMock()

    retrieval_service = AsyncMock()
    retrieval_service.retrieve.return_value = []

    class FailingLLMClient:
        async def stream(self, messages, temperature=0.0):
            yield "this works"
            raise ValueError("Something broke mid-stream")

    orchestrator = ChatOrchestrator(
        chat_service=chat_service,
        retrieval_service=retrieval_service,
        llm_client=FailingLLMClient(),
    )

    chunks = []
    async for chunk in orchestrator.stream_chat(session_id, user_id, "hello"):
        chunks.append(chunk)

    # We should get the error event cleanly
    assert "data: {\"error\": \"An error occurred during completion\"}" in chunks[-1]
    
    # User message was persisted, but assistant message should be skipped or partially saved?
    # In our implementation, we still persist whatever was successfully streamed before the error.
    assert chat_service.add_message.call_count == 2
    assistant_call = chat_service.add_message.mock_calls[1]
    assert assistant_call.kwargs["role"] == "assistant"
    assert assistant_call.kwargs["content"] == "this works"
