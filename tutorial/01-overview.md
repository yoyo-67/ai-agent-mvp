# AI Agent MVP - System Overview

## What We Built

An AI agent system similar to Claude Code with:
- **Backend**: FastAPI + OpenAI API + SSE streaming
- **Frontend**: React + TanStack Router + Tailwind
- **Tools**: File operations (read, write, edit, list, search)

## Architecture

```
┌─────────────────┐     SSE Stream      ┌─────────────────┐
│                 │ ◄────────────────── │                 │
│    Frontend     │                     │    Backend      │
│   (React App)   │ ────────────────► │   (FastAPI)     │
│                 │    POST /api/chat   │                 │
└─────────────────┘                     └────────┬────────┘
                                                 │
                                                 │ Streaming API
                                                 ▼
                                        ┌─────────────────┐
                                        │   OpenAI API    │
                                        │   (GPT-4o)      │
                                        └─────────────────┘
```

## The Flow (Step by Step)

1. **User types message** in the chat UI
2. **Frontend sends POST** to `/api/chat` with message history
3. **Backend receives request** and starts the agent loop
4. **Agent calls OpenAI** with messages + available tools
5. **OpenAI streams response** - either text or tool calls
6. **If tool call**: Backend executes tool, adds result, loops back to step 4
7. **If text**: Backend streams content deltas via SSE
8. **Frontend receives SSE events** and updates UI in real-time
9. **When done**: Backend sends "done" event, frontend finalizes message

## Key Concepts

### SSE (Server-Sent Events)
One-way streaming from server to client. Unlike WebSockets, SSE is:
- Simpler (just HTTP)
- Auto-reconnects
- Perfect for streaming LLM responses

### Agentic Loop
The backend doesn't just call OpenAI once. It loops:
```
while True:
    response = call_openai()
    if response.has_tool_calls:
        execute_tools()
        add_results_to_messages()
        continue  # Loop again
    else:
        return response  # Done
```

### Tool Calling
OpenAI can decide to call tools instead of responding with text:
```json
{
  "tool_calls": [{
    "id": "call_abc123",
    "function": {
      "name": "read_file",
      "arguments": "{\"path\": \"example.py\"}"
    }
  }]
}
```

## File Structure

```
agents/
├── backend/
│   ├── main.py          # FastAPI app, endpoints
│   ├── agent.py         # Agent loop, SSE formatting
│   ├── tools.py         # Tool definitions + execution
│   └── schemas.py       # Pydantic models
├── frontend/
│   └── src/
│       ├── hooks/
│       │   └── useAgentStream.ts   # SSE client hook
│       ├── components/
│       │   ├── ChatWindow.tsx      # Message display
│       │   ├── MessageInput.tsx    # User input
│       │   └── ToolCallCard.tsx    # Tool call UI
│       └── routes/
│           └── index.tsx           # Main page
├── workspace/           # Sandbox for file operations
└── logs/               # Debug logs (network, SSE)
```

## Next Steps

- [02-backend-fastapi.md](./02-backend-fastapi.md) - FastAPI setup and endpoints
- [03-backend-agent-loop.md](./03-backend-agent-loop.md) - The agent loop in depth
- [04-backend-tools.md](./04-backend-tools.md) - Tool definitions and execution
- [05-frontend-streaming.md](./05-frontend-streaming.md) - SSE client and state management
- [06-frontend-components.md](./06-frontend-components.md) - React components
- [07-full-flow-example.md](./07-full-flow-example.md) - Complete request/response walkthrough
