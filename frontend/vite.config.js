import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy API requests to the backend server
    // This will forward all requests starting with /api to the backend server running on http://127.0.0.1:8000
    // With this configuration we can make API requests to the backend without worrying about CORS issues
    // This is hardcoded for now but should be changed to be more dynamic based on environment variables or configuration files
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
})
