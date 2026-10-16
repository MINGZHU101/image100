import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// 开发态通过代理同源访问后端，避免浏览器直连跨域
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 7301,
    strictPort: true,
    proxy: {
      // SSE 单独代理，关闭缓冲以免进度事件被攒批
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
