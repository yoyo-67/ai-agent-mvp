# Full Flow Example

Let's trace a complete request from user input to final response.

## Scenario

User asks: **"What files are in the workspace and what's in sample.txt?"**

## Timeline

```
Time    Frontend                    Backend                     OpenAI
────────────────────────────────────────────────────────────────────────
0ms     User clicks Send
        │
10ms    POST /api/chat ──────────► Receives request
        body: {messages: [...]}     │
                                    │
50ms                                Calls OpenAI ──────────────► Receives request
                                    with tools                   Starts streaming
                                    │
100ms                               ◄─────── tool_calls delta ──
                                    Accumulates: list_files
                                    │
150ms   ◄── tool_call_start ─────── Executes list_files()
        Shows: 🔄 list_files        │
                                    │
160ms   ◄── tool_call_result ────── Result: "example.py\n..."
        Shows: ✅ list_files        │
        (collapsible)               │
                                    │
170ms                               ◄─────── tool_calls delta ──
                                    Accumulates: read_file
                                    │
200ms   ◄── tool_call_start ─────── Executes read_file()
        Shows: 🔄 read_file         │
                                    │
210ms   ◄── tool_call_result ────── Result: "Hello! This is..."
        Shows: ✅ read_file         │
                                    Adds to messages
                                    Loops back to OpenAI ──────► Sees tool results
                                    │
300ms                               ◄─────── content delta ─────
                                    │
310ms   ◄── content_delta ───────── "The"
        Shows: "The▊"               │
                                    │
320ms   ◄── content_delta ───────── " workspace"
        Shows: "The workspace▊"     │
                                    │
...     (many more deltas)
                                    │
800ms   ◄── done ────────────────── finish_reason: stop
        Finalizes message           │
        Removes cursor              │
        │
        Done!
```

## Detailed Breakdown

### Step 1: Frontend Sends Request

```typescript
// useAgentStream.ts - sendMessage()
const apiMessages = [
  { role: 'user', content: "What files are in the workspace and what's in sample.txt?" }
]

await fetchEventSource('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ messages: apiMessages }),
  // ...
})
```

**HTTP Request:**
```
POST /api/chat HTTP/1.1
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "What files are in the workspace and what's in sample.txt?"
    }
  ]
}
```

### Step 2: Backend Receives and Starts Agent Loop

```python
# main.py
@app.post("/api/chat")
async def chat(request: ChatRequest):
    messages = [msg.model_dump() for msg in request.messages]

    async def event_generator():
        async for event_tuple in run_agent_loop(messages):
            yield parse_sse_event(event_tuple)

    return EventSourceResponse(event_generator())
```

### Step 3: First OpenAI Call

```python
# agent.py - run_agent_loop()
messages = [
    {"role": "system", "content": "You are a helpful AI assistant..."},
    {"role": "user", "content": "What files are in the workspace..."}
]

stream = await client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=TOOLS,  # list_files, read_file, etc.
    stream=True
)
```

### Step 4: OpenAI Decides to Call Tools

OpenAI streams back tool calls (not content):

```python
# Stream chunks:
chunk.choices[0].delta.tool_calls = [
    ChoiceDeltaToolCall(index=0, id="call_abc", function=Function(name="list_files", arguments=""))
]
# Then more chunks with arguments...
chunk.choices[0].delta.tool_calls = [
    ChoiceDeltaToolCall(index=0, function=Function(arguments="{}"))
]
# Then another tool:
chunk.choices[0].delta.tool_calls = [
    ChoiceDeltaToolCall(index=1, id="call_xyz", function=Function(name="read_file", arguments=""))
]
# More argument chunks...
chunk.choices[0].delta.tool_calls = [
    ChoiceDeltaToolCall(index=1, function=Function(arguments='{"path":'))
]
chunk.choices[0].delta.tool_calls = [
    ChoiceDeltaToolCall(index=1, function=Function(arguments=' "sample.txt"}'))
]
# Finally:
chunk.choices[0].finish_reason = "tool_calls"
```

After accumulation:
```python
tool_calls = {
    0: {"id": "call_abc", "name": "list_files", "arguments": "{}"},
    1: {"id": "call_xyz", "name": "read_file", "arguments": '{"path": "sample.txt"}'}
}
```

### Step 5: Backend Executes Tools

```python
# Execute list_files
yield format_sse_event("tool_call_start", {
    "id": "call_abc",
    "name": "list_files",
    "arguments": {}
})

result = list_files()  # Returns "example.py\nsample.txt"

yield format_sse_event("tool_call_result", {
    "id": "call_abc",
    "result": "example.py\nsample.txt",
    "is_error": False
})

# Execute read_file
yield format_sse_event("tool_call_start", {
    "id": "call_xyz",
    "name": "read_file",
    "arguments": {"path": "sample.txt"}
})

result = read_file("sample.txt")  # Returns file contents

yield format_sse_event("tool_call_result", {
    "id": "call_xyz",
    "result": "Hello! This is a sample...",
    "is_error": False
})
```

**SSE Events Sent:**
```
event: tool_call_start
data: {"id": "call_abc", "name": "list_files", "arguments": {}}

event: tool_call_result
data: {"id": "call_abc", "result": "example.py\nsample.txt", "is_error": false}

event: tool_call_start
data: {"id": "call_xyz", "name": "read_file", "arguments": {"path": "sample.txt"}}

event: tool_call_result
data: {"id": "call_xyz", "result": "Hello! This is a sample...", "is_error": false}
```

### Step 6: Messages Updated for Next Iteration

```python
messages = [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "What files are in the workspace..."},
    # NEW - Assistant's tool calls:
    {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": "call_abc", "type": "function", "function": {"name": "list_files", "arguments": "{}"}},
            {"id": "call_xyz", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "sample.txt"}'}}
        ]
    },
    # NEW - Tool results:
    {"role": "tool", "tool_call_id": "call_abc", "content": "example.py\nsample.txt"},
    {"role": "tool", "tool_call_id": "call_xyz", "content": "Hello! This is a sample..."}
]
```

### Step 7: Second OpenAI Call (with tool results)

```python
# Loop continues - call OpenAI again with updated messages
stream = await client.chat.completions.create(
    model="gpt-4o",
    messages=messages,  # Now includes tool results
    tools=TOOLS,
    stream=True
)
```

### Step 8: OpenAI Responds with Text

Now OpenAI has the tool results and generates a response:

```python
# Stream chunks with content:
chunk.choices[0].delta.content = "The"
chunk.choices[0].delta.content = " workspace"
chunk.choices[0].delta.content = " contains"
# ...many more...
chunk.choices[0].finish_reason = "stop"
```

Backend yields each delta:
```python
yield format_sse_event("content_delta", {"delta": "The"})
yield format_sse_event("content_delta", {"delta": " workspace"})
# ...
yield format_sse_event("done", {})
```

### Step 9: Frontend Receives and Updates UI

```typescript
// onmessage handler
case 'content_delta':
  accumulatedContent += data.delta
  setCurrentContent(accumulatedContent)
  // UI shows: "The workspace contains▊"
  break

case 'done':
  // Create final message
  const assistantMessage = {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: accumulatedContent,
    toolCalls: accumulatedToolCalls,
  }
  setMessages(prev => [...prev, assistantMessage])
  setCurrentContent('')
  setCurrentToolCalls([])
  break
```

### Final UI State

```
┌─────────────────────────────────────────────────┐
│ 🧑 What files are in the workspace and what's   │
│    in sample.txt?                               │
├─────────────────────────────────────────────────┤
│ 🤖 ┌─────────────────────────────────────────┐  │
│    │ ✅ list_files                        ▶ │  │
│    └─────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────┐  │
│    │ ✅ read_file                         ▶ │  │
│    └─────────────────────────────────────────┘  │
│                                                 │
│    The workspace contains two files:            │
│    - example.py                                 │
│    - sample.txt                                 │
│                                                 │
│    The contents of sample.txt:                  │
│    "Hello! This is a sample text file..."       │
└─────────────────────────────────────────────────┘
```

## Key Takeaways

1. **Streaming is bidirectional context**: Frontend streams to backend (HTTP), backend streams to frontend (SSE)

2. **Tool calls loop**: The agent loop continues until OpenAI returns text instead of tool calls

3. **Accumulation pattern**: Both tool call arguments (backend) and content (frontend) are accumulated from deltas

4. **State management**: Current (streaming) state vs. finalized (messages) state enables smooth UX

5. **Message history grows**: Each tool call adds 2+ messages (assistant + tool responses)

## Debugging Tips

Check the logs:
```bash
# SSE events sent to frontend
tail -f logs/sse.log

# HTTP requests to OpenAI
tail -f logs/network.log

# Backend stdout/stderr
tail -f logs/backend.log
```

Test with curl:
```bash
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"List files"}]}'
```
