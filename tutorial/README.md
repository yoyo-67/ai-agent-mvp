# AI Agent MVP Tutorial

A step-by-step guide to understanding how this AI agent system works.

## Quick Start

```bash
# Terminal 1 - Backend
cd backend && source .venv/bin/activate
uvicorn main:app --reload --port 8002

# Terminal 2 - Frontend
cd frontend && npm run dev

# Open http://localhost:3002
```

## Tutorial Index

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| [01](./01-overview.md) | **Overview** | Architecture, key concepts, file structure |
| [02](./02-backend-fastapi.md) | **FastAPI Setup** | App creation, CORS, endpoints, SSE |
| [03](./03-backend-agent-loop.md) | **Agent Loop** | Streaming, tool accumulation, the loop |
| [04](./04-backend-tools.md) | **Tools** | Tool definitions, implementation, sandboxing |
| [05](./05-frontend-streaming.md) | **SSE Hook** | useAgentStream, state management |
| [06](./06-frontend-components.md) | **Components** | ChatWindow, MessageInput, ToolCallCard |
| [07](./07-full-flow-example.md) | **Full Flow** | Complete request walkthrough with timeline |

## Reading Order

**If you're new to this codebase:**
1. Start with [01-overview.md](./01-overview.md) for the big picture
2. Read [07-full-flow-example.md](./07-full-flow-example.md) to see how it all connects
3. Deep dive into specific areas as needed

**If you want to modify the backend:**
- [02-backend-fastapi.md](./02-backend-fastapi.md)
- [03-backend-agent-loop.md](./03-backend-agent-loop.md) (most important)
- [04-backend-tools.md](./04-backend-tools.md)

**If you want to modify the frontend:**
- [05-frontend-streaming.md](./05-frontend-streaming.md) (most important)
- [06-frontend-components.md](./06-frontend-components.md)

## Key Files

```
backend/
├── main.py      # FastAPI app, /api/chat endpoint
├── agent.py     # The agent loop (core logic)
├── tools.py     # Tool definitions and implementations
└── schemas.py   # Pydantic models

frontend/src/
├── hooks/useAgentStream.ts  # SSE client (core logic)
├── components/
│   ├── ChatWindow.tsx       # Message list
│   ├── MessageInput.tsx     # User input
│   └── ToolCallCard.tsx     # Tool call display
└── routes/index.tsx         # Main page
```

## Common Tasks

### Add a new tool

1. Add definition to `TOOLS` array in `tools.py`
2. Implement the function
3. Add to `TOOL_FUNCTIONS` dict
4. That's it! The agent will automatically have access

### Change the model

Edit `agent.py`:
```python
async def run_agent_loop(
    messages: list[dict[str, Any]],
    model: str = "gpt-4o-mini"  # Change here
)
```

### Add a new SSE event type

1. Backend: Add `yield format_sse_event("new_event", {...})` in agent.py
2. Frontend: Add `case 'new_event':` in useAgentStream.ts

## Debugging

```bash
# Watch SSE events
tail -f logs/sse.log

# Watch OpenAI API calls
tail -f logs/network.log

# Test backend directly
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```
