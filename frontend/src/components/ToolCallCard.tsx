import { useState } from 'react'
import type { ToolCall } from '../hooks/useAgentStream'

interface ToolCallCardProps {
  toolCall: ToolCall
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const statusColors = {
    pending: 'bg-gray-400',
    running: 'bg-yellow-400 animate-pulse',
    done: toolCall.isError ? 'bg-red-500' : 'bg-green-500',
  }

  return (
    <div className="my-2 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors"
      >
        <span className={`w-2 h-2 rounded-full ${statusColors[toolCall.status]}`} />
        <span className="font-mono text-sm text-gray-700 dark:text-gray-300">
          {toolCall.name}
        </span>
        <span className="text-gray-400 text-xs">
          {toolCall.status === 'running' ? 'Running...' : toolCall.status === 'done' ? 'Complete' : 'Pending'}
        </span>
        <svg
          className={`w-4 h-4 ml-auto text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-4 py-3 space-y-3 bg-white dark:bg-gray-900">
          <div>
            <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Arguments</div>
            <pre className="text-xs bg-gray-100 dark:bg-gray-800 rounded p-2 overflow-x-auto">
              {JSON.stringify(toolCall.arguments, null, 2)}
            </pre>
          </div>

          {toolCall.result !== undefined && (
            <div>
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Result {toolCall.isError && <span className="text-red-500">(Error)</span>}
              </div>
              <pre className={`text-xs rounded p-2 overflow-x-auto whitespace-pre-wrap ${
                toolCall.isError
                  ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                  : 'bg-gray-100 dark:bg-gray-800'
              }`}>
                {toolCall.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
