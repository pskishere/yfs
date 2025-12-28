import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [['babel-plugin-react-compiler']],
      },
    }),
  ],
  server: {
    port: 3000,
    // 允许所有域名访问（包括 ngrok 等反向代理域名）
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  css: {
    // 配置 CSS 处理
    devSourcemap: true,
  },
  build: {
    // 优化构建输出
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // 确保 chunk 文件正确分割
        manualChunks: undefined,
        // 优化文件命名
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
      },
    },
    // 确保源映射正确生成（生产环境可以关闭）
    sourcemap: false,
    // 使用 esbuild 进行最小化（默认，更稳定）
    minify: 'esbuild',
    // 禁用 CSS minify，避免 lightningcss 的 :global 语法问题
    // 或者使用 esbuild 处理 CSS（如果支持）
    cssMinify: false,
  },
})
