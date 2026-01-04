"""
FastAPI backend for AI Agent MVP.

Provides:
- POST /api/chat: SSE streaming endpoint for agent interaction
- GET /api/health: Health check endpoint
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load environment variables BEFORE importing agent
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from agent import run_agent_loop, parse_sse_event
from schemas import ChatRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: verify OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set. Copy .env.example to .env and add your key.")
    yield
    # Shutdown: cleanup if needed
    pass


# Create FastAPI app
app = FastAPI(
    title="AI Agent MVP",
    description="An AI agent with MCP-style file operation tools",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint with SSE streaming.

    Accepts messages and returns a stream of events:
    - content_delta: Streaming text chunks
    - tool_call_start: Tool execution starting
    - tool_call_result: Tool execution result
    - done: Stream complete
    """
    # Convert Pydantic models to dicts for agent
    messages = [msg.model_dump(exclude_none=True) for msg in request.messages]

    async def event_generator():
        async for event_tuple in run_agent_loop(messages):
            yield parse_sse_event(event_tuple)

    return EventSourceResponse(event_generator())


# =============================================================================
# Run with uvicorn
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
