import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from app.core.exceptions import ConfigurationError
from app.llm.llm_client import LLMClient
from app.retrieval.context_builder import RetrievedChunk
from app.services.chat_service import ChatService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


def build_prompt(question: str, context_chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    system_prompt = (
        "You are a code-intelligence assistant analyzing a software repository.\n"
        "Use the provided context to answer the user's question accurately.\n"
        "If the context is insufficient to answer the question, clearly state that you do not have enough information.\n"
        "Do not invent facts about the repository.\n"
    )

    if context_chunks:
        context_str = "\n\n".join(
            f"--- {chunk.source_type.upper()}: {chunk.label} (File: {chunk.file_path}) ---\n{chunk.chunk_text}"
            for chunk in context_chunks
        )
        system_prompt += f"\n\nContext:\n{context_str}"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]


class ChatOrchestrator:
    def __init__(
        self,
        chat_service: ChatService,
        retrieval_service: RetrievalService,
        llm_client: LLMClient | None,
    ) -> None:
        self.chat_service = chat_service
        self.retrieval_service = retrieval_service
        self.llm_client = llm_client

    async def stream_chat(
        self, session_id: UUID, user_id: UUID, message_content: str
    ) -> AsyncGenerator[str, None]:
        if self.llm_client is None:
            raise ConfigurationError("LLM client is not configured. Cannot process chat.")

        # 1. Validate session & repository access (get_session throws if invalid)
        chat_session = await self.chat_service.get_session(session_id, user_id)

        # 2. Persist user message
        await self.chat_service.add_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=message_content,
        )

        # 3. Retrieve context
        chunks = await self.retrieval_service.retrieve(
            repository_id=chat_session.repository_id,
            question=message_content,
        )

        # 4. Build prompt
        messages = build_prompt(message_content, chunks)

        # Format sources for persistence exactly how the schema expects them (JSONB array)
        sources_meta = [
            {
                "source_type": c.source_type,
                "source_id": c.source_id,
                "label": c.label,
                "file_path": c.file_path,
                "score": c.score,
            }
            for c in chunks
        ]

        assistant_content = ""

        try:
            # 5. Stream LLM response
            stream = self.llm_client.stream(messages=messages, temperature=0.0)
            async for chunk in stream:
                assistant_content += chunk
                # Emit SSE event chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Emit final completion event
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception:
            logger.exception("Error during LLM stream")
            yield f"data: {json.dumps({'error': 'An error occurred during completion'})}\n\n"
            # We do NOT re-raise to avoid crashing the open HTTP stream abruptly with a 500,
            # which breaks the SSE protocol. The error event signals the client.

        # 6. Persist assistant message if any content was generated
        if assistant_content:
            await self.chat_service.add_message(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=assistant_content,
                sources=sources_meta,
            )
