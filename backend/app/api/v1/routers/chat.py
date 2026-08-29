from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.v1.deps import CurrentUser, get_chat_orchestrator, get_chat_service
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionRead,
    ChatSessionUpdate,
)
from app.services.chat_orchestrator import ChatOrchestrator
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    data: ChatSessionCreate,
    current_user: CurrentUser,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatSessionRead:
    session = await service.create_session(current_user.id, data)
    return ChatSessionRead.model_validate(session)


@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_chat_sessions(
    repository_id: UUID,
    current_user: CurrentUser,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> list[ChatSessionRead]:
    sessions = await service.list_sessions(repository_id, current_user.id)
    return [ChatSessionRead.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionRead)
async def get_chat_session(
    session_id: UUID,
    current_user: CurrentUser,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatSessionRead:
    session = await service.get_session(session_id, current_user.id)
    return ChatSessionRead.model_validate(session)


@router.patch("/sessions/{session_id}", response_model=ChatSessionRead)
async def update_chat_session(
    session_id: UUID,
    data: ChatSessionUpdate,
    current_user: CurrentUser,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatSessionRead:
    session = await service.rename_session(session_id, current_user.id, data)
    return ChatSessionRead.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: UUID,
    current_user: CurrentUser,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> None:
    await service.delete_session(session_id, current_user.id)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
async def list_chat_messages(
    session_id: UUID,
    current_user: CurrentUser,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> list[ChatMessageRead]:
    messages = await service.list_messages(session_id, current_user.id)
    return [ChatMessageRead.model_validate(m) for m in messages]


@router.post("/sessions/{session_id}/stream", status_code=status.HTTP_200_OK)
async def stream_chat_message(
    session_id: UUID,
    message: ChatMessageCreate,
    current_user: CurrentUser,
    orchestrator: Annotated[ChatOrchestrator, Depends(get_chat_orchestrator)],
) -> StreamingResponse:
    """Stream an assistant response to a user's message using Server-Sent Events."""
    
    # We return the StreamingResponse immediately. 
    # The generator internally performs session validation, inserts the user message,
    # retrieves context, and formats the LLM stream yielding SSE chunks.
    return StreamingResponse(
        orchestrator.stream_chat(
            session_id=session_id,
            user_id=current_user.id,
            message_content=message.content,
        ),
        media_type="text/event-stream",
    )
