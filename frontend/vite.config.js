import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const rootDir = resolve(__dirname, '..')
  const env = loadEnv(mode, rootDir, '')
  const backendProxyTarget =
    env.VITE_BACKEND_PROXY_TARGET || 'http://127.0.0.1:8010'
  const aiProxyTarget = env.VITE_AI_PROXY_TARGET || 'http://127.0.0.1:8001'

  return {
    envDir: rootDir,
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    server: {
      port: 5173,
      proxy: {
        '/ai-api': {
          target: aiProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ai-api/, '')
        },
        '/backend-api': {
          target: backendProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/backend-api/, '')
        }
      }
    }
  }
})
