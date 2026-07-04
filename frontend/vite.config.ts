import basicSsl from "@vitejs/plugin-basic-ssl";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  server: {
    // Serve the dev server over HTTPS (self-signed cert via basic-ssl below) and bind to all
    // interfaces, so opening it from a phone on the LAN is a secure context. The mic
    // (navigator.mediaDevices) and precise geolocation only exist over https:// or on localhost.
    allowedHosts: ['.devtunnels.ms'], //allow devtunnels.ms to proxy to this server (for LAN access from a phone)
    host: true,
    proxy: {
      // Forward /api straight through - the backend serves its routes under /api (see
      // backend/app/main.py), so dev and the single-origin production container use the exact
      // same paths. (No rewrite: the prefix is the contract, not a dev-only artifact.)
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  plugins: [
    basicSsl(),
    react(),
    VitePWA({
      registerType: "autoUpdate",
      // Favicon + apple-touch aren't build outputs, so precache them explicitly (they live in
      // public/assets/ alongside the other icons and are served from /assets/).
      includeAssets: ["assets/favicon.svg", "assets/favicon.png", "assets/apple-touch-icon.png"],
      manifest: {
        name: "MTBirb",
        short_name: "MTBirb",
        description: "Find mountain bike trails with great birdwatching and wildlife odds",
        theme_color: "#2f5d3a",
        background_color: "#2f5d3a",
        display: "standalone",
        // Icons live in public/assets/ and are served from /assets/. "maskable" gives Android/iOS
        // an adaptive icon (art kept inside the safe zone); the two "any" sizes cover install +
        // Lighthouse installability.
        icons: [
          { src: "/assets/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
          { src: "/assets/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
          { src: "/assets/icon-512-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
    }),
  ],
});
