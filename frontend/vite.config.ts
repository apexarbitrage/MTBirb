import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "MTBirb",
        short_name: "MTBirb",
        description: "Find mountain bike trails with great birdwatching and wildlife odds",
        theme_color: "#2f5d3a",
        background_color: "#2f5d3a",
        display: "standalone",
        // TODO: add real icons (192x192, 512x512) under public/icons before shipping -
        // installability/Lighthouse PWA checks need them, omitted here to avoid a broken reference.
      },
    }),
  ],
});
