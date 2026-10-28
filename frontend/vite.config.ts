import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss(), react()],
  server: {
    // /api is proxied to the backend. In Docker (the supported runtime),
    // deploy/docker-compose.yml injects VITE_BACKEND_PROXY_TARGET pointing at
    // the backend's Docker service hostname (e.g. http://transportfinder-backend:10022).
    // The localhost fallback below only matters when this dev server runs outside Docker.
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
