"""
Agent loop with streaming support.

The agent loop handles:
1. Streaming responses from OpenAI
2. Accumulating tool calls from delta chunks
3. Executing tools and feeding results back
4. Yielding SSE events to the frontend
"""

import json
import logging
import os
from typing import Any, AsyncGenerator, cast

import httpx
from openai import AsyncOpenAI

# Setup logging - file only, no console output
logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(logs_dir, exist_ok=True)

# Network logging (httpx/httpcore) - file only
network_log_path = os.path.join(logs_dir, "network.log")
network_handler = logging.FileHandler(network_log_path)
network_handler.setLevel(logging.DEBUG)
network_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(message)s"))

httpx_logger = logging.getLogger("httpx")
httpx_logger.addHandler(network_handler)
httpx_logger.setLevel(logging.DEBUG)
httpx_logger.propagate = False  # Don't output to console

httpcore_logger = logging.getLogger("httpcore")
httpcore_logger.addHandler(network_handler)
httpcore_logger.setLevel(logging.DEBUG)
httpcore_logger.propagate = False  # Don't output to console

# SSE event logging - file only
sse_log_path = os.path.join(logs_dir, "sse.log")
sse_handler = logging.FileHandler(sse_log_path)
sse_handler.setLevel(logging.DEBUG)
sse_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
sse_logger = logging.getLogger("sse")
sse_logger.addHandler(sse_handler)
sse_logger.setLevel(logging.DEBUG)
sse_logger.propagate = False  # Don't output to console
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from tools import TOOLS, execute_tool

# Lazy client initialization
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Get or create the OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        # Disable SSL verification (mitmproxy in use)
        http_client = httpx.AsyncClient(verify=False)
        _client = AsyncOpenAI(api_key=api_key, http_client=http_client)
    return _client

# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful AI assistant with access to file operation tools.
You can read, write, edit, list, and search files in the workspace.
Always use the tools when the user asks about files or needs file operations.
Be concise and helpful in your responses."""


# =============================================================================
# SSE Event Formatting
# =============================================================================

def format_sse_event(event: str, data: dict[str, Any]) -> tuple[str, str]:
    """Format data as an SSE event tuple (event_name, json_data)."""
    json_data = json.dumps(data)
    sse_logger.debug(f"event: {event} | data: {json_data}")
    return (event, json_data)


def parse_sse_event(event_tuple: tuple[str, str]) -> dict[str, str]:
    """Parse SSE event tuple to dict for sse_starlette."""
    return {"event": event_tuple[0], "data": event_tuple[1]}


# =============================================================================
# Tool Call Accumulation
# =============================================================================

def init_tool_call(tc_delta: Any) -> dict[str, Any]:
    """Initialize a new tool call from the first delta."""
    return {
        "id": tc_delta.id,
        "name": tc_delta.function.name if tc_delta.function else None,
        "arguments": ""
    }


def accumulate_tool_call(tool_call: dict[str, Any], tc_delta: Any) -> None:
    """Accumulate tool call arguments from a delta chunk."""
    if tc_delta.function and tc_delta.function.arguments:
        tool_call["arguments"] += tc_delta.function.arguments


def process_tool_calls_delta(
    tool_calls: dict[int, dict[str, Any]],
    delta_tool_calls: list[Any]
) -> None:
    """Process tool call deltas and accumulate into tool_calls dict."""
    for tc_delta in delta_tool_calls:
        idx = tc_delta.index

        if idx not in tool_calls:
            tool_calls[idx] = init_tool_call(tc_delta)
        else:
            accumulate_tool_call(tool_calls[idx], tc_delta)


# =============================================================================
# Tool Execution
# =============================================================================

async def execute_tool_calls(
    tool_calls: dict[int, dict[str, Any]]
) -> AsyncGenerator[tuple[tuple[str, str], dict[str, Any] | None], None]:
    """
    Execute accumulated tool calls and yield SSE events.
    Yields tuples of (event_string, result_dict or None).
    """
    for tc in tool_calls.values():
        tool_id = tc["id"]
        tool_name = tc["name"]

        try:
            arguments = json.loads(tc["arguments"])
        except json.JSONDecodeError as e:
            yield format_sse_event("tool_call_start", {
                "id": tool_id,
                "name": tool_name,
                "arguments": {},
                "error": f"Invalid JSON arguments: {e}"
            }), {
                "id": tool_id,
                "result": f"Error: Invalid JSON arguments: {e}",
                "is_error": True
            }
            continue

        # Emit tool_call_start
        yield format_sse_event("tool_call_start", {
            "id": tool_id,
            "name": tool_name,
            "arguments": arguments
        }), None

        # Execute the tool
        result = execute_tool(tool_name, arguments)
        is_error = result.startswith("Error:")

        # Emit tool_call_result
        yield format_sse_event("tool_call_result", {
            "id": tool_id,
            "result": result,
            "is_error": is_error
        }), {
            "id": tool_id,
            "result": result,
            "is_error": is_error
        }


def build_tool_call_messages(
    tool_calls: dict[int, dict[str, Any]],
    results: list[dict[str, Any]]
) -> list[ChatCompletionMessageParam]:
    """Build messages to add after tool execution."""
    # Assistant message with tool_calls
    assistant_tool_calls = [
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

    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": assistant_tool_calls  # type: ignore[typeddict-item]
        }
    ]

    # Tool response messages
    for r in results:
        messages.append({
            "role": "tool",
            "tool_call_id": r["id"],
            "content": r["result"]
        })

    return messages


# =============================================================================
# Main Agent Loop
# =============================================================================

async def run_agent_loop(
    messages: list[dict[str, Any]],
    model: str = "gpt-4o"
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Run the agentic loop with streaming.

    This is an async generator that yields SSE-formatted events:
    - content_delta: Streaming text chunks
    - tool_call_start: Tool execution starting
    - tool_call_result: Tool execution result
    - done: Stream complete

    The loop continues until the LLM returns a final response (no tool calls).
    """
    # Add system prompt if not present
    if not messages or messages[0].get("role") != "system":
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    # Cast messages to proper type
    typed_messages = cast(list[ChatCompletionMessageParam], messages)
    typed_tools = cast(list[ChatCompletionToolParam], TOOLS)

    while True:
        # Create streaming completion
        stream = await get_client().chat.completions.create(
            model=model,
            messages=typed_messages,
            tools=typed_tools,
            stream=True
        )

        # Process the stream
        tool_calls: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None

        async for chunk in stream:
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta
            finish_reason = choice.finish_reason

            # Stream content deltas
            if delta.content:
                yield format_sse_event("content_delta", {"delta": delta.content})

            # Accumulate tool calls
            if delta.tool_calls:
                process_tool_calls_delta(tool_calls, delta.tool_calls)

        # Handle tool calls
        if finish_reason == "tool_calls" and tool_calls:
            # Execute tools and yield events
            results: list[dict[str, Any]] = []
            async for event, result in execute_tool_calls(tool_calls):
                yield event
                if result is not None:
                    results.append(result)

            # Build messages for next iteration
            new_messages = build_tool_call_messages(tool_calls, results)
            typed_messages.extend(new_messages)

            # Continue loop for next LLM response
            continue

        # No tool calls - we're done
        yield format_sse_event("done", {})
        return
