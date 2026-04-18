import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: path.resolve(__dirname, 'propio/public/js/app'),
    emptyOutDir: false,
    lib: {
      entry: path.resolve(__dirname, 'propio/public/js/app/main.bundle.js'),
      name: 'PropioApp',
      fileName: () => 'main.bundle.js',
      formats: ['iife'],
    },
    rollupOptions: {
      output: {
        assetFileNames: '../css/[name][extname]',
      },
    },
  },
})
