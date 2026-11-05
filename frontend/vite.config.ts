import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const apiProxy = {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: false,
  },
};

export default defineConfig({
  plugins: [react()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
  test: {
    environment: "jsdom",
    restoreMocks: true,
    clearMocks: true,
    setupFiles: ["./src/testSetup.ts"],
  },
});
