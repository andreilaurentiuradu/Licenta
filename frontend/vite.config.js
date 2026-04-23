import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // ascultă pe 0.0.0.0 (necesar în container)
    proxy: {
      '/api': {
        target: process.env.BACKEND_URL || 'http://localhost:5000',
        changeOrigin: true,
      },
      '/realms': {
        target: process.env.KC_URL || 'http://localhost:8180',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals:     true,
    environment: 'jsdom',
    setupFiles:  './src/test/setup.js',
    css:         true,
  },
})
