import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The dev server runs on 5173 (the origin the FastAPI CORS config allows).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
})
