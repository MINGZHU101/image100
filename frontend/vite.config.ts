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
      '/api': {
        target: 'http://127.0.0.1:7302',
        changeOrigin: true,
      },
    },
  },
})
