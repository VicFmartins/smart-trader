import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/auth": "http://127.0.0.1:8000",
      "/upload": "http://127.0.0.1:8000",
      "/clients": "http://127.0.0.1:8000",
      "/accounts": "http://127.0.0.1:8000",
      "/assets": "http://127.0.0.1:8000",
      "/positions": "http://127.0.0.1:8000",
      "/ingestion-reports": "http://127.0.0.1:8000",
      "/etl": "http://127.0.0.1:8000"
    }
  }
});
