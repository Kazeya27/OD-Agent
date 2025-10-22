#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OD Agent Service - FastAPI service for chatbot."""

from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from threading import Lock

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

# Import from od_agent
import sys

sys.path.append(str(Path(__file__).resolve().parent))
from tools import TOOLS, set_base_url as set_backend_url
from od_agent import SYSTEM_PROMPT, get_llm

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env")
load_dotenv(_HERE.parent / "backend" / ".env")

# ---------------------------------------------------------------------------
# Chat History Storage
# ---------------------------------------------------------------------------

CHAT_HISTORY_DIR = _HERE / "chat_history"
CHAT_HISTORY_DIR.mkdir(exist_ok=True)

_STORE: Dict[str, ChatMessageHistory] = {}
_HISTORY_LOCK = Lock()


class ChatMessage(BaseModel):
    """Single chat message entry."""

    time: str = Field(..., description="ISO8601 timestamp")
    from_: str = Field(
        ...,
        alias="from",
        description="Message source: user|assistant|function_call|function_response",
    )
    content: str = Field(..., description="Message content")

    class Config:
        populate_by_name = True


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Get or create chat history for a session."""
    with _HISTORY_LOCK:
        if session_id not in _STORE:
            _STORE[session_id] = ChatMessageHistory()
            # Try to load from file
            _load_session_from_file(session_id)
        return _STORE[session_id]


def _get_session_file_path(session_id: str) -> Path:
    """Get file path for session history."""
    return CHAT_HISTORY_DIR / f"{session_id}.json"


def _load_session_from_file(session_id: str) -> None:
    """Load session history from file if exists."""
    file_path = _get_session_file_path(session_id)
    if not file_path.exists():
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            messages = json.load(f)

        # Reconstruct chat history from messages
        history = _STORE[session_id]
        for msg in messages:
            from_type = msg.get("from")
            content = msg.get("content", "")

            if from_type == "user":
                history.add_user_message(content)
            elif from_type == "assistant":
                history.add_ai_message(content)
            # function_call and function_response are handled separately
    except Exception as e:
        print(f"Error loading session {session_id}: {e}")


def save_message_to_history(session_id: str, from_type: str, content: str) -> None:
    """Save a single message to session history file."""
    file_path = _get_session_file_path(session_id)

    message = {
        "time": datetime.now().isoformat(),
        "from": from_type,
        "content": content,
    }

    with _HISTORY_LOCK:
        # Load existing messages
        messages = []
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    messages = json.load(f)
            except Exception as e:
                print(f"Error reading history file: {e}")
                messages = []

        # Append new message
        messages.append(message)

        # Save back to file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing history file: {e}")


def get_chat_history(session_id: str) -> List[ChatMessage]:
    """Get all chat messages for a session."""
    file_path = _get_session_file_path(session_id)

    if not file_path.exists():
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            messages = json.load(f)
        return [ChatMessage(**msg) for msg in messages]
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []


# ---------------------------------------------------------------------------
# Agent Builder
# ---------------------------------------------------------------------------


def build_agent(
    provider: str = "gemini",
    model_name: str = "gemini-2.5-flash-preview-05-20",
    temperature: float = 0.6,
) -> RunnableWithMessageHistory:
    """Build the agent with specified configuration."""
    llm = get_llm(provider, model_name, temperature)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent_runnable = create_tool_calling_agent(llm, TOOLS, prompt)
    executor = AgentExecutor(
        agent=agent_runnable,
        tools=TOOLS,
        verbose=True,
        return_intermediate_steps=True,
    )

    return RunnableWithMessageHistory(
        executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(title="OD Agent Service", version="1.0.0", description="OD 智能问答服务")

# Global agent instance
_AGENT: Optional[RunnableWithMessageHistory] = None


class ChatRequest(BaseModel):
    """Request for chat endpoint."""

    session_id: str = Field(..., description="Session ID for conversation continuity")
    question: str = Field(..., description="User question")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    session_id: str
    answer: str
    timestamp: str


class HistoryRequest(BaseModel):
    """Request for getting chat history."""

    session_id: str = Field(..., description="Session ID")


class HistoryResponse(BaseModel):
    """Response containing chat history."""

    session_id: str
    messages: List[ChatMessage]


@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup."""
    global _AGENT

    # Get configuration from environment
    provider = os.getenv("LLM_PROVIDER", "gemini")
    model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash-preview-05-20")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.6"))
    backend_url = os.getenv("BASE_URL", "http://127.0.0.1:8502")

    # Set backend URL
    if backend_url:
        set_backend_url(backend_url)

    # Build agent
    _AGENT = build_agent(provider, model_name, temperature)
    print(
        f"Agent initialized: provider={provider}, model={model_name}, temp={temperature}"
    )


@app.get("/")
async def root():
    """Health check."""
    return {"ok": True, "service": "OD Agent Service", "version": "1.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the agent.

    Args:
        request: ChatRequest containing session_id and question

    Returns:
        ChatResponse with agent\'s answer
    """
    if _AGENT is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    session_id = request.session_id
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Save user message
    save_message_to_history(session_id, "user", question)

    try:
        # Invoke agent
        config = {"configurable": {"session_id": session_id}}
        response = _AGENT.invoke({"input": question}, config=config)

        # Extract answer
        answer = response.get("output", str(response))

        # Log intermediate steps (function calls)
        intermediate_steps = response.get("intermediate_steps", [])
        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]

                # Log function call
                function_call_content = json.dumps(
                    {
                        "tool": action.tool,
                        "tool_input": action.tool_input,
                    },
                    ensure_ascii=False,
                )
                save_message_to_history(
                    session_id, "function_call", function_call_content
                )

                # Log function response
                save_message_to_history(
                    session_id, "function_response", str(observation)
                )

        # Save assistant message
        save_message_to_history(session_id, "assistant", answer)

        return ChatResponse(
            session_id=session_id, answer=answer, timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        error_msg = f"Agent error: {str(e)}"
        save_message_to_history(session_id, "assistant", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/history", response_model=HistoryResponse)
async def get_history(request: HistoryRequest):
    """
    Get chat history for a session.

    Args:
        request: HistoryRequest containing session_id

    Returns:
        HistoryResponse with all messages in the session
    """
    session_id = request.session_id
    messages = get_chat_history(session_id)

    return HistoryResponse(session_id=session_id, messages=messages)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("AGENT_PORT", "8503"))
    uvicorn.run(app, host="127.0.0.1", port=port)
