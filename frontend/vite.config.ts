import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Explicit per-path entries, not a blanket '/' proxy — a catch-all would
    // also proxy away the dev server's own '/', '/@vite/client', and the HMR
    // websocket. CLAUDE.md's locked structure spec calls this out as the
    // intended way to avoid CORS setup on the backend.
    proxy: {
      "/documents": "http://localhost:8000",
      "/query": "http://localhost:8000",
      "/ask": "http://localhost:8000",
    },
  },
})
