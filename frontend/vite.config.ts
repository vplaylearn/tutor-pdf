import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Build output goes into backend/public so the FastAPI function serves the
// frontend same-origin on Vercel.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../backend/public',
    emptyOutDir: true,
  },
});
