import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" — statik fayllar aiohttp orqali /assets/ yo'lidan xizmat qilinadi,
// nisbiy yo'llar har qanday joylashuvda ishlashini kafolatlaydi.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist",
    assetsDir: "assets",
  },
  server: {
    port: 5173,
  },
});
