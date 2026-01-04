# Frontend - SSE Streaming Hook

The `useAgentStream` hook is the **brain of the frontend**. It manages state and handles the SSE connection.

## The Hook Structure

```typescript
export function useAgentStream() {
  // State
  const [messages, setMessages] = useState<Message[]>([])
  const [currentContent, setCurrentContent] = useState('')
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Actions
  const sendMessage = useCallback(async (content: string) => { ... }, [messages])
  const clearMessages = useCallback(() => { ... }, [])

  return {
    messages,           // Completed messages
    currentContent,     // Streaming text (in progress)
    currentToolCalls,   // Current tool calls (in progress)
    isStreaming,        // Is currently streaming?
    error,              // Error message if any
    sendMessage,        // Send a new message
    clearMessages,      // Clear chat history
  }
}
```

## Types

```typescript
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCall[]
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: string
  isError?: boolean
  status: 'pending' | 'running' | 'done'
}
```

## The sendMessage Function

This is where the magic happens:

```typescript
const sendMessage = useCallback(async (content: string) => {
  // 1. Reset state
  setError(null)
  setCurrentContent('')
  setCurrentToolCalls([])
  setIsStreaming(true)

  // 2. Add user message to UI immediately
  const userMessage: Message = {
    id: crypto.randomUUID(),
    role: 'user',
    content,
  }
  setMessages(prev => [...prev, userMessage])

  // 3. Prepare messages for API
  const apiMessages = [...messages, userMessage].map(m => ({
    role: m.role,
    content: m.content,
  }))

  // 4. Track accumulated values
  let accumulatedContent = ''
  let accumulatedToolCalls: ToolCall[] = []

  // 5. Connect to SSE stream
  try {
    await fetchEventSource('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: apiMessages }),
      onmessage(event) {
        // Handle each SSE event...
      },
      onerror(err) {
        setError('Connection error')
        throw err  // Stop retrying
      },
      onclose() {
        setIsStreaming(false)
      },
    })
  } catch (err) {
    setError(err.message)
  } finally {
    setIsStreaming(false)
  }
}, [messages])
```

## SSE Event Handling

The `onmessage` callback handles each event type:

```typescript
onmessage(event) {
  const data = JSON.parse(event.data)

  switch (event.event) {
    case 'content_delta': {
      // Append text to current content
      const { delta } = data
      accumulatedContent += delta
      setCurrentContent(accumulatedContent)
      break
    }

    case 'tool_call_start': {
      // Add new tool call with "running" status
      const { id, name, arguments: args } = data
      const toolCall: ToolCall = {
        id,
        name,
        arguments: args,
        status: 'running',
      }
      accumulatedToolCalls = [...accumulatedToolCalls, toolCall]
      setCurrentToolCalls([...accumulatedToolCalls])
      break
    }

    case 'tool_call_result': {
      // Update tool call with result
      const { id, result, is_error } = data
      accumulatedToolCalls = accumulatedToolCalls.map(tc =>
        tc.id === id
          ? { ...tc, result, isError: is_error, status: 'done' }
          : tc
      )
      setCurrentToolCalls([...accumulatedToolCalls])
      break
    }

    case 'done': {
      // Finalize - create the assistant message
      if (accumulatedContent || accumulatedToolCalls.length > 0) {
        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: accumulatedContent,
          toolCalls: accumulatedToolCalls.length > 0
            ? accumulatedToolCalls
            : undefined,
        }
        setMessages(prev => [...prev, assistantMessage])
      }

      // Reset streaming state
      setCurrentContent('')
      setCurrentToolCalls([])
      break
    }
  }
}
```

## State Flow Diagram

```
User clicks Send
       │
       ▼
┌─────────────────────┐
│ setIsStreaming(true)│
│ Add user message    │
│ Clear current state │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│ Connect to SSE      │────►│ content_delta       │
└──────────┬──────────┘     │ setCurrentContent() │
           │                └─────────────────────┘
           │
           │                ┌─────────────────────┐
           ├───────────────►│ tool_call_start     │
           │                │ Add to toolCalls[]  │
           │                └─────────────────────┘
           │
           │                ┌─────────────────────┐
           ├───────────────►│ tool_call_result    │
           │                │ Update toolCall     │
           │                └─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ done event          │
│ Create Message      │
│ Add to messages[]   │
│ Clear current state │
│ setIsStreaming(false)│
└─────────────────────┘
```

## Why Two States?

We have **current** state (streaming) and **messages** state (completed):

```typescript
// While streaming:
currentContent = "Hello, I'll help you..."  // Growing
currentToolCalls = [{...status: 'running'}]  // In progress

// After done:
currentContent = ""  // Reset
currentToolCalls = []  // Reset
messages = [
  { role: 'user', content: '...' },
  { role: 'assistant', content: 'Hello...', toolCalls: [...] }  // Finalized
]
```

This allows the UI to:
1. Show streaming text with a cursor/animation
2. Show tool calls in progress
3. Keep completed messages stable

## fetchEventSource Library

We use `@microsoft/fetch-event-source` instead of native EventSource because:
- Native EventSource only supports GET
- We need POST with a JSON body

```bash
npm install @microsoft/fetch-event-source
```

```typescript
import { fetchEventSource } from '@microsoft/fetch-event-source'

await fetchEventSource('/api/chat', {
  method: 'POST',  // Not possible with native EventSource
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ messages }),
  onmessage(event) { ... },
  onerror(err) { ... },
  onclose() { ... },
})
```

## Error Handling

```typescript
onerror(err) {
  console.error('SSE Error:', err)
  setError('Connection error. Please try again.')
  setIsStreaming(false)
  throw err  // Throwing stops retry attempts
}
```

The library auto-retries by default. We throw to stop retries on error.

## Next

[06-frontend-components.md](./06-frontend-components.md) - React components
