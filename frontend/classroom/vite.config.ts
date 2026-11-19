import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(root, '../static/classroom')
const publishedHtml = path.resolve(root, '../static/ubuntu-isizulu-beginner-i-classroom.html')

function publishClassroomPage(): Plugin {
  return {
    name: 'publish-classroom-page',
    closeBundle() {
      const built = path.join(outDir, 'index.html')
      const html = fs.readFileSync(built, 'utf8')
      fs.writeFileSync(publishedHtml, html)
    },
  }
}

export default defineConfig({
  root,
  base: '/classroom/',
  plugins: [react(), publishClassroomPage()],
  build: {
    outDir,
    emptyOutDir: true,
    assetsDir: '.',
    cssCodeSplit: false,
    rollupOptions: {
      input: path.join(root, 'index.html'),
      output: {
        entryFileNames: 'classroom.js',
        chunkFileNames: 'classroom-[name].js',
        assetFileNames: (info) => (info.name?.endsWith('.css') ? 'classroom.css' : 'media/[name][extname]'),
      },
    },
  },
})
