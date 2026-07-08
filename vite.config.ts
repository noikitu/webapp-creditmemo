import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  base: './',
  server: { host: '127.0.0.1', port: 5175 },
  resolve: { dedupe: ['vue', 'vue-router'], alias: { '@': path.resolve(__dirname, './src') } },
})
