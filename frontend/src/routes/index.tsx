import { createFileRoute } from '@tanstack/react-router'
import { useAgentStream } from '../hooks/useAgentStream'
import { ChatWindow } from '../components/ChatWindow'
import { MessageInput } from '../components/MessageInput'

export const Route = createFileRoute('/')({
  component: ChatPage,
})

function ChatPage() {
  const {
    messages,
    currentContent,
    currentToolCalls,
    isStreaming,
    error,
    sendMessage,
    clearMessages,
  } = useAgentStream()

  return (
    <div className="flex flex-col h-full">
      {error && (
        <div className="mx-4 mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <ChatWindow
        messages={messages}
        currentContent={currentContent}
        currentToolCalls={currentToolCalls}
        isStreaming={isStreaming}
      />

      <div className="flex items-center gap-2 px-4 pb-2">
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            Clear chat
          </button>
        )}
      </div>

      <MessageInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  )
}
