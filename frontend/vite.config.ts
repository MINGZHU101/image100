import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

// 开发态同源代理后端；SSE 关闭缓冲以免进度事件被攒批
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: '127.0.0.1',
    port: 7301,
    strictPort: true,
    proxy: {
      '/api/events': {
        target: 'http://127.0.0.1:7302',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['cache-control'] = 'no-cache'
            proxyRes.headers['x-accel-buffering'] = 'no'
          })
        },
      },
      '/api': {
        target: 'http://127.0.0.1:7302',
        changeOrigin: true,
      },
    },
  },
})
