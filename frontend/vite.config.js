import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  // Relative base so the demo works under /ufc-data-insights-web-app/ on Pages.
  base: process.env.VITE_DEMO === 'true' ? './' : '/',
  plugins: [react()],
})
