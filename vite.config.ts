import { defineConfig } from 'vite';
export default defineConfig({
  root: '.',
  server: { proxy: {
    '/api':'http://127.0.0.1:8765',
    '/board':'http://127.0.0.1:8765',
    '/assets/board.jpg':'http://127.0.0.1:8765'
  }},
  build: { outDir: 'dist', emptyOutDir:true }
});
