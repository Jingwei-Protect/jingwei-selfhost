import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        // Local Jingwei API (avoid 8000 — often taken by other projects / WinError 10013)
        target: 'http://127.0.0.1:8010',
        // ASCII/halftone preview can take 20–40s; adv-protect + HF download can take minutes
        timeout: 600_000,
        proxyTimeout: 600_000,
      },
    },
  },
})
