import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { svelteTesting } from "@testing-library/svelte/vite";

export default defineConfig({
  plugins: [svelte(), svelteTesting()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.js"],
    include: ["tests/**/*.test.js"],
    // Vitest 4: poolOptions are now top-level
    pool: "forks",
    poolOptions: undefined,
    singleFork: true,
    // Vitest 4: cache dir uses Vite's cacheDir instead
  },
  cacheDir: "node_modules/.vite-cache",
  optimizeDeps: {
    include: ["svelte", "@testing-library/svelte"],
  },
  resolve: {
    conditions: ["browser"],
  },
});