# AI Agent MVP

A minimal AI agent system with streaming responses and file operation tools, built with FastAPI and React.

## Features

- **Streaming Responses** - Real-time text streaming via Server-Sent Events (SSE)
- **Tool Calling** - LLM can execute file operations autonomously
- **Agentic Loop** - Continues calling tools until task is complete
- **Modern UI** - React chat interface with dark mode support
- **File Tools** - Read, write, edit, list, and search files in a sandboxed workspace

## Architecture

```
┌─────────────────┐     SSE Stream      ┌─────────────────┐
│    Frontend     │ ◄────────────────── │    Backend      │
│   (React)       │ ────────────────►   │   (FastAPI)     │
└─────────────────┘    POST /api/chat   └────────┬────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │   OpenAI API    │
                                        │   (GPT-4o)      │
                                        └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key
- [uv](https://github.com/astral-sh/uv) (recommended for Python)

### Quick Run (Warp Terminal)

If you use Warp terminal, source the aliases file for quick commands:

```bash
# Add to your .zshrc or source directly
export AGENTS_ROOT="/path/to/agents"  # Optional, defaults to ~/Work/agents
source /path/to/agents/__aliases/alias.sh

# Then use these commands:
agents-dev      # Start both backend and frontend in new tabs
agents-backend  # Start only backend
agents-frontend # Start only frontend
agents          # cd to project directory
```

### Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run server
uvicorn main:app --reload --port 8002
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Open http://localhost:3000 and start chatting!

## Project Structure

```
agents/
├── backend/
│   ├── main.py          # FastAPI app, endpoints
│   ├── agent.py         # Agent loop, streaming
│   ├── tools.py         # Tool definitions
│   └── schemas.py       # Pydantic models
├── frontend/
│   └── src/
│       ├── hooks/       # useAgentStream SSE hook
│       ├── components/  # React components
│       └── routes/      # TanStack Router pages
├── workspace/           # Sandboxed file operations
├── tutorial/            # In-depth documentation
└── logs/                # Debug logs (gitignored)
```

## Available Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read contents of a file |
| `write_file` | Create or overwrite a file |
| `edit_file` | Replace text in a file |
| `list_files` | List files matching a glob pattern |
| `search_files` | Search for patterns in files (grep-like) |

All file operations are sandboxed to the `workspace/` directory.

## Example Prompts

Try these with the agent:

- "What files are in the workspace?"
- "Read sample.txt and summarize it"
- "Add a docstring to the greet function in example.py"
- "Search for 'config' in all files"
- "Create a new file called notes.txt with a todo list"

## API Endpoints

### `POST /api/chat`

Send messages and receive streaming SSE response.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "List the files"}
  ]
}
```

**SSE Events:**
- `content_delta` - Streaming text chunk
- `tool_call_start` - Tool execution starting
- `tool_call_result` - Tool execution result
- `done` - Stream complete

### `GET /api/health`

Health check endpoint.

## Logs

All debug logs are written to the `logs/` folder (gitignored, never committed):

```
logs/
├── backend.log   # Uvicorn server output (stdout/stderr)
├── frontend.log  # Vite dev server output
├── sse.log       # All SSE events sent to frontend
└── network.log   # HTTP requests to OpenAI API (httpx/httpcore)
```

### What's in each log?

| Log File | Contents | Use Case |
|----------|----------|----------|
| `backend.log` | Server startup, errors, request logs | General backend debugging |
| `frontend.log` | Vite compilation, HMR updates | Frontend build issues |
| `sse.log` | Every SSE event with timestamp | Debug streaming, tool calls |
| `network.log` | Full HTTP request/response to OpenAI | API issues, token usage |

### Watching logs in real-time

```bash
# Watch SSE events (most useful for debugging agent behavior)
tail -f logs/sse.log

# Watch OpenAI API calls
tail -f logs/network.log

# Watch all logs at once
tail -f logs/*.log
```

### Log format examples

**sse.log:**
```
2024-01-04 14:54:40,302 - event: tool_call_start | data: {"id": "call_abc", "name": "read_file", ...}
2024-01-04 14:54:40,303 - event: tool_call_result | data: {"id": "call_abc", "result": "file contents..."}
2024-01-04 14:54:40,936 - event: content_delta | data: {"delta": "Here are"}
2024-01-04 14:54:43,949 - event: done | data: {}
```

**network.log:**
```
2024-01-04 14:54:39 - httpx - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
```

## Tutorial

See the `tutorial/` folder for detailed documentation on how everything works:

1. **01-overview.md** - Architecture & concepts
2. **02-backend-fastapi.md** - FastAPI setup
3. **03-backend-agent-loop.md** - The agent loop (core logic)
4. **04-backend-tools.md** - Tool definitions
5. **05-frontend-streaming.md** - SSE hook
6. **06-frontend-components.md** - React components
7. **07-full-flow-example.md** - Complete request walkthrough

## Configuration

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key (required) |

## License

MIT
