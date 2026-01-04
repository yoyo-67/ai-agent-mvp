# Backend - FastAPI Setup

## Entry Point: main.py

The FastAPI app is the HTTP server that receives requests from the frontend.

### App Creation

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Agent MVP",
    description="An AI agent with MCP-style file operation tools",
    version="0.1.0",
    lifespan=lifespan
)
```

### CORS Configuration

CORS (Cross-Origin Resource Sharing) allows the frontend (different port) to call the backend:

```python
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
```

**Why multiple ports?** Vite may use different ports if 3000 is busy.

### Lifespan Handler

Runs on startup/shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set")
    yield
    # Shutdown
    pass
```

## Endpoints

### Health Check

```python
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }
```

### Chat Endpoint (SSE Streaming)

This is the main endpoint. It returns an **SSE stream**, not JSON:

```python
from sse_starlette.sse import EventSourceResponse

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Convert Pydantic models to dicts
    messages = [msg.model_dump(exclude_none=True) for msg in request.messages]

    async def event_generator():
        async for event_tuple in run_agent_loop(messages):
            yield parse_sse_event(event_tuple)

    return EventSourceResponse(event_generator())
```

**Key points:**
1. `ChatRequest` is a Pydantic model that validates the input
2. `run_agent_loop` is an async generator that yields SSE events
3. `EventSourceResponse` streams events to the client

## Request/Response Format

### Request (from frontend)

```json
POST /api/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "List the files"}
  ]
}
```

### Response (SSE Stream)

```
event: content_delta
data: {"delta": "Here are"}

event: content_delta
data: {"delta": " the files:"}

event: tool_call_start
data: {"id": "call_123", "name": "list_files", "arguments": {}}

event: tool_call_result
data: {"id": "call_123", "result": "example.py\nsample.txt", "is_error": false}

event: done
data: {}
```

## Schemas (schemas.py)

Pydantic models for request validation:

```python
from pydantic import BaseModel

class Message(BaseModel):
    role: str  # "user", "assistant", "system", "tool"
    content: str | None = None
    tool_call_id: str | None = None  # For tool responses

class ChatRequest(BaseModel):
    messages: list[Message]
```

## Environment Variables

The backend needs `OPENAI_API_KEY`. We use python-dotenv:

```python
from dotenv import load_dotenv

# Load BEFORE importing agent (which uses the key)
load_dotenv()

from agent import run_agent_loop  # Now key is available
```

**.env file:**
```
OPENAI_API_KEY=sk-...
```

## Running the Backend

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8002
```

The `--reload` flag enables hot-reloading when code changes.

## Next

[03-backend-agent-loop.md](./03-backend-agent-loop.md) - How the agent loop works
