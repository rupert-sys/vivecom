import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/setupTests.ts'],
    // 5s (default) no alcanza en el contenedor Docker de desarrollo de este
    // proyecto (sin Node.js nativo en el host, I/O de virtiofs es lento) para
    // pruebas que escriben en varios campos + esperan una llamada async.
    testTimeout: 15000,
  },
})
