import { createRootRoute, Outlet } from '@tanstack/react-router'
import { ThemeToggle } from '../components/ThemeToggle'

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 transition-colors">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h1 className="text-xl font-semibold">AI Agent MVP</h1>
        <ThemeToggle />
      </header>
      <main className="h-[calc(100vh-73px)]">
        <Outlet />
      </main>
    </div>
  )
}
