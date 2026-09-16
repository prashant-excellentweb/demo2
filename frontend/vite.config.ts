import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxying keeps the browser on a single origin in development, so the
      // httpOnly session cookie behaves exactly as it does in production.
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    // The markdown renderer pulls in highlight.js, which is large and changes
    // far less often than app code. Splitting it out means a deploy only
    // invalidates the app chunk, not the whole download.
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return undefined;
          if (
            /highlight\.js|lowlight|react-markdown|remark|rehype|mdast|hast|micromark|unist|vfile|property-information|space-separated|comma-separated|character-entities|devlop|estree|decode-named/.test(
              id,
            )
          ) {
            return "vendor-markdown";
          }
          if (/[\\/]react[\\/]|react-dom|react-router|scheduler/.test(id)) {
            return "vendor-react";
          }
          return "vendor";
        },
      },
    },
  },
});
