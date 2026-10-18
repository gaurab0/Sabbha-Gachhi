import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // In Docker the app is bind-mounted from the host and node_modules is an
  // anonymous (root-owned) volume, so the non-root `node` user cannot write
  // Vite's default cache at node_modules/.vite. VITE_CACHE_DIR points it at a
  // writable path (/tmp/.vite) in the dev container; unset = Vite's default.
  cacheDir: process.env.VITE_CACHE_DIR || undefined,
  server: {
    host: '0.0.0.0',
    watch: {
      usePolling: process.env.CHOKIDAR_USEPOLLING === 'true',
    },
  },
})
