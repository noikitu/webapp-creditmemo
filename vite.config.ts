import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// The built SPA is served by WEBAIKU from dist/ inside DSS. `base: ''` keeps
// asset URLs relative (./assets/...) so WEBAIKU's bs_init can rewrite them to
// absolute backend URLs. Do NOT use vite-plugin-singlefile here.
// Locally, Vite proxies /api to the Flask dev backend (VITE_API_PORT, default 5000).
const apiPort = Number(process.env.VITE_API_PORT || '5000')

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  base: '',
  server: {
    host: '127.0.0.1',
    port: Number(process.env.VITE_CLIENT_PORT || '5175'),
    proxy: {
      '/api': { target: `http://127.0.0.1:${apiPort}`, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
  resolve: {
    dedupe: ['vue', 'vue-router'],
    alias: { '@': path.resolve(__dirname, './src') },
  },
})
