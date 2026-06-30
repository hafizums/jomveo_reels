import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174, // Running on 5174 to avoid conflict with the legacy dev port
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/generated": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
