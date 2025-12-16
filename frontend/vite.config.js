import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The build output directory must match the Jinja2Templates directory in FastAPI's main.py
export default defineConfig({
  plugins: [react()],
  // IMPORTANT: Set base path to match the FastAPI static mount
  base: '/static/', 
  build: {
    outDir: 'dist',
    assetsDir: 'assets', // This is Vite's default, no need to change
    emptyOutDir: true,
  },
  server: {
    proxy: {
        // Proxy API calls to the FastAPI backend during development
        '/scrape': 'http://127.0.0.1:8000',
        '/healthz': 'http://127.0.0.1:8000',
    }
  }
})