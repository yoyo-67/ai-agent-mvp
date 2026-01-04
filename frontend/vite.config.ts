import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import path from 'path'
import fs from 'fs'

// Read backend port from .ports.env
function getBackendPort(): string {
  const portsEnvPath = path.resolve(__dirname, '../.ports.env')
  try {
    const content = fs.readFileSync(portsEnvPath, 'utf-8')
    const match = content.match(/BACKEND_PORT=(\d+)/)
    if (match) {
      return match[1]
    }
  } catch {
    // File doesn't exist, use default
  }
  return process.env.VITE_API_PORT || '8000'
}

const apiPort = getBackendPort()
console.log(`Proxying /api to http://localhost:${apiPort}`)

export default defineConfig({
  plugins: [
    TanStackRouterVite(),
    react(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: `http://localhost:${apiPort}`,
        changeOrigin: true,
      },
    },
  },
})
