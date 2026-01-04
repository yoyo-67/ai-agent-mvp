import { useEffect, useRef } from 'react'
import type { Message, ToolCall } from '../hooks/useAgentStream'
import { ToolCallCard } from './ToolCallCard'

interface ChatWindowProps {
  messages: Message[]
  currentContent: string
  currentToolCalls: ToolCall[]
  isStreaming: boolean
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
        }`}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>

        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.toolCalls.map(tc => (
              <ToolCallCard key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function ChatWindow({
  messages,
  currentContent,
  currentToolCalls,
  isStreaming,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentContent, currentToolCalls])

  const hasContent = messages.length > 0 || currentContent || currentToolCalls.length > 0

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {!hasContent && (
        <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
          <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
          <p className="text-lg font-medium">Start a conversation</p>
          <p className="text-sm mt-1">Ask me to read, write, or search files in the workspace</p>
        </div>
      )}

      {messages.map(message => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {/* Streaming content */}
      {(currentContent || currentToolCalls.length > 0) && (
        <div className="flex justify-start">
          <div className="max-w-[80%] rounded-2xl px-4 py-3 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
            {currentContent && (
              <div className={`whitespace-pre-wrap ${isStreaming && !currentToolCalls.length ? 'typing-cursor' : ''}`}>
                {currentContent}
              </div>
            )}

            {currentToolCalls.length > 0 && (
              <div className="mt-3 space-y-2">
                {currentToolCalls.map(tc => (
                  <ToolCallCard key={tc.id} toolCall={tc} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
