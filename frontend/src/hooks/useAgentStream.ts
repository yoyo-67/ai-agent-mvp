import { useState, useCallback } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source'

// =============================================================================
// Types
// =============================================================================

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

interface ContentDeltaEvent {
  delta: string
}

interface ToolCallStartEvent {
  id: string
  name: string
  arguments: Record<string, unknown>
}

interface ToolCallResultEvent {
  id: string
  result: string
  is_error: boolean
}

// =============================================================================
// Hook
// =============================================================================

export function useAgentStream() {
  const [messages, setMessages] = useState<Message[]>([])
  const [currentContent, setCurrentContent] = useState('')
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(async (content: string) => {
    // Reset state
    setError(null)
    setCurrentContent('')
    setCurrentToolCalls([])
    setIsStreaming(true)

    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
    }
    setMessages(prev => [...prev, userMessage])

    // Prepare messages for API (exclude IDs, include only what backend needs)
    const apiMessages = [...messages, userMessage].map(m => ({
      role: m.role,
      content: m.content,
    }))

    let accumulatedContent = ''
    let accumulatedToolCalls: ToolCall[] = []

    try {
      await fetchEventSource('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messages: apiMessages }),

        onmessage(event) {
          const data = JSON.parse(event.data)

          switch (event.event) {
            case 'content_delta': {
              const { delta } = data as ContentDeltaEvent
              accumulatedContent += delta
              setCurrentContent(accumulatedContent)
              break
            }

            case 'tool_call_start': {
              const { id, name, arguments: args } = data as ToolCallStartEvent
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
              const { id, result, is_error } = data as ToolCallResultEvent
              accumulatedToolCalls = accumulatedToolCalls.map(tc =>
                tc.id === id
                  ? { ...tc, result, isError: is_error, status: 'done' as const }
                  : tc
              )
              setCurrentToolCalls([...accumulatedToolCalls])
              break
            }

            case 'done': {
              // Finalize assistant message
              if (accumulatedContent || accumulatedToolCalls.length > 0) {
                const assistantMessage: Message = {
                  id: crypto.randomUUID(),
                  role: 'assistant',
                  content: accumulatedContent,
                  toolCalls: accumulatedToolCalls.length > 0 ? accumulatedToolCalls : undefined,
                }
                setMessages(prev => [...prev, assistantMessage])
              }

              // Reset streaming state
              setCurrentContent('')
              setCurrentToolCalls([])
              accumulatedContent = ''
              accumulatedToolCalls = []
              break
            }
          }
        },

        onerror(err) {
          console.error('SSE Error:', err)
          setError('Connection error. Please try again.')
          setIsStreaming(false)
          throw err // Stop retrying
        },

        onclose() {
          setIsStreaming(false)
        },
      })
    } catch (err) {
      console.error('Stream error:', err)
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsStreaming(false)
    }
  }, [messages])

  const clearMessages = useCallback(() => {
    setMessages([])
    setCurrentContent('')
    setCurrentToolCalls([])
    setError(null)
  }, [])

  return {
    messages,
    currentContent,
    currentToolCalls,
    isStreaming,
    error,
    sendMessage,
    clearMessages,
  }
}
