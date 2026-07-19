import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      // 前端 /ai-api/... → 杨云天的 AI 服务 http://localhost:8001/...
      '/ai-api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ai-api/, '')
      },
      // 前端 /backend-api/... → 王宏伟后端服务（占位）
      '/backend-api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/backend-api/, '')
      }
    }
  }
})
