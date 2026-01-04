# Frontend - React Components

## Component Tree

```
App (routes/index.tsx)
├── ThemeToggle
└── ChatWindow
    ├── MessageBubble (for each message)
    │   └── ToolCallCard (for each tool call)
    ├── StreamingMessage (current content + tool calls)
    │   └── ToolCallCard
    └── MessageInput
```

## ChatWindow

The main container that displays messages and handles scrolling:

```tsx
export function ChatWindow() {
  const {
    messages,
    currentContent,
    currentToolCalls,
    isStreaming,
    error,
    sendMessage,
  } = useAgentStream()

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentContent])

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Streaming content */}
        {(currentContent || currentToolCalls.length > 0) && (
          <StreamingMessage
            content={currentContent}
            toolCalls={currentToolCalls}
          />
        )}

        {/* Error display */}
        {error && (
          <div className="text-red-500 p-2 rounded bg-red-100">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <MessageInput
        onSend={sendMessage}
        disabled={isStreaming}
      />
    </div>
  )
}
```

## MessageBubble

Displays a single completed message:

```tsx
interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg p-3 ${
          isUser
            ? 'bg-blue-500 text-white'
            : 'bg-gray-100 dark:bg-gray-800'
        }`}
      >
        {/* Tool calls (if any) */}
        {message.toolCalls?.map(tc => (
          <ToolCallCard key={tc.id} toolCall={tc} />
        ))}

        {/* Message content */}
        {message.content && (
          <div className="prose dark:prose-invert">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
```

## ToolCallCard

Shows tool execution with collapsible details:

```tsx
interface ToolCallCardProps {
  toolCall: ToolCall
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="border rounded-lg mb-2 overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700"
      >
        <div className="flex items-center gap-2">
          {/* Status indicator */}
          {toolCall.status === 'running' ? (
            <span className="animate-spin">⏳</span>
          ) : toolCall.isError ? (
            <span>❌</span>
          ) : (
            <span>✅</span>
          )}

          {/* Tool name */}
          <span className="font-mono text-sm">{toolCall.name}</span>
        </div>

        {/* Expand/collapse icon */}
        <span>{isExpanded ? '▼' : '▶'}</span>
      </button>

      {/* Details - collapsible */}
      {isExpanded && (
        <div className="p-2 text-sm">
          {/* Arguments */}
          <div className="mb-2">
            <span className="font-semibold">Arguments:</span>
            <pre className="bg-gray-100 dark:bg-gray-800 p-2 rounded mt-1 overflow-x-auto">
              {JSON.stringify(toolCall.arguments, null, 2)}
            </pre>
          </div>

          {/* Result */}
          {toolCall.result && (
            <div>
              <span className="font-semibold">Result:</span>
              <pre className="bg-gray-100 dark:bg-gray-800 p-2 rounded mt-1 overflow-x-auto whitespace-pre-wrap">
                {toolCall.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

## MessageInput

The input field with send button:

```tsx
interface MessageInputProps {
  onSend: (content: string) => void
  disabled?: boolean
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [input, setInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={disabled}
          className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2"
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50"
        >
          {disabled ? 'Sending...' : 'Send'}
        </button>
      </div>
    </form>
  )
}
```

## ThemeToggle

Light/dark mode switch:

```tsx
export function ThemeToggle() {
  const [isDark, setIsDark] = useState(() => {
    // Check localStorage or system preference
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme')
      if (saved) return saved === 'dark'
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return false
  })

  useEffect(() => {
    // Apply theme to document
    document.documentElement.classList.toggle('dark', isDark)
    localStorage.setItem('theme', isDark ? 'dark' : 'light')
  }, [isDark])

  return (
    <button
      onClick={() => setIsDark(!isDark)}
      className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
    >
      {isDark ? '🌙' : '☀️'}
    </button>
  )
}
```

## StreamingMessage

Shows content while it's being streamed:

```tsx
interface StreamingMessageProps {
  content: string
  toolCalls: ToolCall[]
}

export function StreamingMessage({ content, toolCalls }: StreamingMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] rounded-lg p-3 bg-gray-100 dark:bg-gray-800">
        {/* Tool calls in progress */}
        {toolCalls.map(tc => (
          <ToolCallCard key={tc.id} toolCall={tc} />
        ))}

        {/* Streaming content with cursor */}
        {content && (
          <div className="prose dark:prose-invert">
            <ReactMarkdown>{content}</ReactMarkdown>
            <span className="animate-pulse">▊</span>
          </div>
        )}
      </div>
    </div>
  )
}
```

## Tailwind Dark Mode

Configure Tailwind for class-based dark mode:

```js
// tailwind.config.js
module.exports = {
  darkMode: 'class',  // Use 'class' strategy
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Then in CSS/HTML:

```html
<html class="dark">  <!-- Added by ThemeToggle -->
  <body class="bg-white dark:bg-gray-900 text-black dark:text-white">
```

## Next

[07-full-flow-example.md](./07-full-flow-example.md) - Complete request walkthrough
