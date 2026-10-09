import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend serves the built app at http://127.0.0.1:8000/app, so assets live under /app/.
// During development (npm run dev), API calls are forwarded to the FastAPI server on port 8000.
const API = "http://127.0.0.1:8000";
const apiPaths = ["/auth", "/injury", "/pain", "/engine", "/insurance", "/recovery-model", "/autoencoder", "/rag"];

export default defineConfig({
  plugins: [react()],
  base: "/app/",
  server: {
    port: 5173,
    proxy: Object.fromEntries(apiPaths.map(p => [p, API])),
  },
  build: { outDir: "dist", emptyOutDir: true },
});
