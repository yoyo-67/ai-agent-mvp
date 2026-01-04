# Backend - The Agent Loop

This is the **heart of the system**. The agent loop is what makes it "agentic" - it can call tools and loop until the task is complete.

## The Main Function

```python
async def run_agent_loop(
    messages: list[dict[str, Any]],
    model: str = "gpt-4o"
) -> AsyncGenerator[tuple[str, str], None]:
```

**Key points:**
- `async` - Uses async/await for non-blocking I/O
- `AsyncGenerator` - Yields values over time (streaming)
- Returns `tuple[str, str]` - (event_name, json_data)

## The Loop Structure

```python
async def run_agent_loop(messages, model="gpt-4o"):
    # Add system prompt if not present
    if not messages or messages[0].get("role") != "system":
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    while True:  # ← The agentic loop
        # 1. Call OpenAI (streaming)
        stream = await get_client().chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            stream=True
        )

        # 2. Process the stream
        tool_calls = {}
        finish_reason = None

        async for chunk in stream:
            # Handle content and tool calls...
            pass

        # 3. If tool calls, execute and continue loop
        if finish_reason == "tool_calls" and tool_calls:
            # Execute tools, add results to messages
            # continue  ← Loop again!
            pass

        # 4. No tool calls = done
        yield format_sse_event("done", {})
        return
```

## Understanding Streaming

OpenAI streams responses in **chunks**. Each chunk contains a **delta** (partial update):

```python
async for chunk in stream:
    choice = chunk.choices[0]
    delta = choice.delta
    finish_reason = choice.finish_reason

    # Text content comes in pieces
    if delta.content:
        yield format_sse_event("content_delta", {"delta": delta.content})

    # Tool calls also come in pieces
    if delta.tool_calls:
        process_tool_calls_delta(tool_calls, delta.tool_calls)
```

### Content Delta Example

When the LLM says "Hello, how can I help?", you get:

```
chunk 1: delta.content = "Hello"
chunk 2: delta.content = ","
chunk 3: delta.content = " how"
chunk 4: delta.content = " can"
chunk 5: delta.content = " I"
chunk 6: delta.content = " help"
chunk 7: delta.content = "?"
chunk 8: finish_reason = "stop"
```

## Tool Call Accumulation

Tool calls are **also streamed in pieces**. The tricky part: the JSON arguments come in fragments!

```
chunk 1: tool_calls[0].id = "call_abc", function.name = "read_file"
chunk 2: tool_calls[0].function.arguments = '{"pa'
chunk 3: tool_calls[0].function.arguments = 'th":'
chunk 4: tool_calls[0].function.arguments = ' "exa'
chunk 5: tool_calls[0].function.arguments = 'mple.py"}'
chunk 6: finish_reason = "tool_calls"
```

We accumulate using an **index-based dictionary**:

```python
def process_tool_calls_delta(tool_calls, delta_tool_calls):
    for tc_delta in delta_tool_calls:
        idx = tc_delta.index  # 0, 1, 2... for multiple tools

        if idx not in tool_calls:
            # First chunk - initialize
            tool_calls[idx] = {
                "id": tc_delta.id,
                "name": tc_delta.function.name,
                "arguments": ""
            }
        else:
            # Subsequent chunks - append arguments
            if tc_delta.function and tc_delta.function.arguments:
                tool_calls[idx]["arguments"] += tc_delta.function.arguments
```

After all chunks, `tool_calls[0]["arguments"]` = `'{"path": "example.py"}'`

## Tool Execution

When `finish_reason == "tool_calls"`, we execute each tool:

```python
async for event, result in execute_tool_calls(tool_calls):
    yield event
    if result:
        results.append(result)
```

The `execute_tool_calls` function:

```python
async def execute_tool_calls(tool_calls):
    for tc in tool_calls.values():
        tool_id = tc["id"]
        tool_name = tc["name"]
        arguments = json.loads(tc["arguments"])

        # Emit start event
        yield format_sse_event("tool_call_start", {
            "id": tool_id,
            "name": tool_name,
            "arguments": arguments
        }), None

        # Execute the tool
        result = execute_tool(tool_name, arguments)
        is_error = result.startswith("Error:")

        # Emit result event
        yield format_sse_event("tool_call_result", {
            "id": tool_id,
            "result": result,
            "is_error": is_error
        }), {"id": tool_id, "result": result, "is_error": is_error}
```

## Building Messages for Next Iteration

After tool execution, we add messages and **loop again**:

```python
def build_tool_call_messages(tool_calls, results):
    messages = []

    # 1. Assistant message with tool_calls (what the LLM asked for)
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"]
                }
            }
            for tc in tool_calls.values()
        ]
    })

    # 2. Tool response messages (the results)
    for r in results:
        messages.append({
            "role": "tool",
            "tool_call_id": r["id"],
            "content": r["result"]
        })

    return messages
```

## SSE Event Formatting

Events are formatted as tuples for sse_starlette:

```python
def format_sse_event(event: str, data: dict) -> tuple[str, str]:
    json_data = json.dumps(data)
    sse_logger.debug(f"event: {event} | data: {json_data}")
    return (event, json_data)

def parse_sse_event(event_tuple: tuple[str, str]) -> dict[str, str]:
    return {"event": event_tuple[0], "data": event_tuple[1]}
```

**Output format:**
```
event: content_delta
data: {"delta": "Hello"}

event: done
data: {}
```

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Loop                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐                                           │
│  │ Call OpenAI  │◄────────────────────────────────┐         │
│  └──────┬───────┘                                 │         │
│         │                                         │         │
│         ▼                                         │         │
│  ┌──────────────┐                                 │         │
│  │Process Stream│                                 │         │
│  └──────┬───────┘                                 │         │
│         │                                         │         │
│         ▼                                         │         │
│  ┌──────────────────────┐    Yes    ┌───────────────────┐   │
│  │ finish_reason ==     │──────────►│ Execute Tools     │   │
│  │ "tool_calls"?        │           │ Add to messages   │───┘
│  └──────────┬───────────┘           └───────────────────┘   │
│             │ No                                             │
│             ▼                                                │
│  ┌──────────────┐                                           │
│  │ Yield "done" │                                           │
│  │ Return       │                                           │
│  └──────────────┘                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Next

[04-backend-tools.md](./04-backend-tools.md) - Tool definitions and execution
