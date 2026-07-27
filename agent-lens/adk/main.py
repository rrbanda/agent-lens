"""Agent Lens ADK — FastAPI server with OpenAI-compatible /chat/completions.

Production entrypoint: uvicorn adk.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from os import getenv

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from google.genai import types
from pydantic import BaseModel, Field

from adk.agent import APP_NAME, get_runner
from adk.tracing import enable_tracing

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OpenAI-compatible request / response models
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str = Field(..., examples=["user", "assistant", "system"])
    content: str = Field(..., examples=["Show me all experiments"])


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    model: str | None = Field(None)
    stream: bool = Field(False)


class ChoiceMessage(BaseModel):
    role: str = Field("assistant")
    content: str


class Choice(BaseModel):
    index: int
    message: ChoiceMessage
    finish_reason: str = Field("stop")


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = Field("chat.completion")
    created: int
    model: str
    choices: list[Choice]
    context: list[dict] | None = None
    usage: dict | None = None


class HealthResponse(BaseModel):
    status: str
    agent_initialized: bool


# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
runner = None
USER_ID = "api_user"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global runner
    enable_tracing()

    base_url = getenv("BASE_URL") or getenv("OPENAI_BASE_URL")
    model_id = getenv("MODEL_ID") or getenv("ADK_MODEL")
    api_key = getenv("API_KEY") or getenv("OPENAI_API_KEY") or getenv("GOOGLE_API_KEY")

    runner = get_runner(model_id=model_id, base_url=base_url, api_key=api_key)
    yield
    runner = None


app = FastAPI(
    title="Agent Lens (ADK)",
    description="AI agent evaluation platform — OpenAI-compatible chat completions API.",
    lifespan=lifespan,
)


def _make_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:12]}"


def _extract_user_message(messages: list[ChatMessage]) -> str:
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    raise HTTPException(status_code=400, detail="No user message found")


@app.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    if runner is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    user_content = _extract_user_message(request.messages)
    model_id = request.model or getenv("MODEL_ID") or getenv("ADK_MODEL") or "agent-lens"

    if request.stream:
        return await _handle_stream(user_content, model_id)
    return await _handle_chat(user_content, model_id)


async def _handle_chat(user_content: str, model_id: str) -> dict:
    try:
        session = await runner.session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID
        )
        new_message = types.Content(
            role="user", parts=[types.Part.from_text(text=user_content)]
        )

        final_text = ""
        context_messages: list[dict] = []

        async for event in runner.run_async(
            user_id=USER_ID, session_id=session.id, new_message=new_message
        ):
            if not event.content or not event.content.parts:
                continue
            for part in event.content.parts:
                if part.function_call:
                    context_messages.append({
                        "role": "assistant",
                        "content": f"Calling tool: {part.function_call.name}",
                        "tool_calls": [{
                            "type": "function",
                            "function": {
                                "name": part.function_call.name,
                                "arguments": json.dumps(
                                    dict(part.function_call.args) if part.function_call.args else {}
                                ),
                            },
                        }],
                    })
                elif part.function_response:
                    context_messages.append({
                        "role": "tool",
                        "name": part.function_response.name,
                        "content": json.dumps(
                            dict(part.function_response.response) if part.function_response.response else {}
                        ),
                    })
                elif part.text:
                    role = event.content.role or "model"
                    context_messages.append({
                        "role": "assistant" if role == "model" else role,
                        "content": part.text,
                    })
                    if role == "model":
                        final_text = part.text

        return {
            "id": _make_id(),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_id,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": final_text},
                "finish_reason": "stop",
            }],
            "context": context_messages,
            "usage": None,
        }
    except Exception:
        logger.exception("Error processing chat completion")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _handle_stream(user_content: str, model_id: str) -> StreamingResponse:
    completion_id = _make_id()
    created = int(time.time())

    async def event_generator() -> AsyncIterator[str]:
        try:
            session = await runner.session_service.create_session(
                app_name=APP_NAME, user_id=USER_ID
            )
            new_message = types.Content(
                role="user", parts=[types.Part.from_text(text=user_content)]
            )

            async for event in runner.run_async(
                user_id=USER_ID, session_id=session.id, new_message=new_message
            ):
                if not event.content or not event.content.parts:
                    continue
                for part in event.content.parts:
                    if part.function_call:
                        data = {
                            "id": completion_id, "object": "chat.completion.chunk",
                            "created": created, "model": model_id,
                            "choices": [{"index": 0, "delta": {
                                "role": "assistant",
                                "tool_calls": [{"index": 0, "type": "function", "function": {
                                    "name": part.function_call.name,
                                    "arguments": json.dumps(dict(part.function_call.args) if part.function_call.args else {}),
                                }}],
                            }, "finish_reason": None}],
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    elif part.function_response:
                        data = {
                            "id": completion_id, "object": "chat.completion.chunk",
                            "created": created, "model": model_id,
                            "choices": [{"index": 0, "delta": {
                                "role": "tool",
                                "content": json.dumps(dict(part.function_response.response) if part.function_response.response else {}),
                                "name": part.function_response.name,
                            }, "finish_reason": None}],
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    elif part.text:
                        data = {
                            "id": completion_id, "object": "chat.completion.chunk",
                            "created": created, "model": model_id,
                            "choices": [{"index": 0, "delta": {"content": part.text}, "finish_reason": None}],
                        }
                        yield f"data: {json.dumps(data)}\n\n"

            yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model_id, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            logger.exception("Error in stream")
            yield f"data: {json.dumps({'error': {'message': 'Internal server error', 'type': 'server_error'}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    initialized = runner is not None
    body = {"status": "healthy" if initialized else "not_ready", "agent_initialized": initialized}
    if not initialized:
        return JSONResponse(status_code=503, content=body)
    return body


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(getenv("PORT", "8000")))
