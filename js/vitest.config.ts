import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    // Shared filesystem fixtures run serially in local test runs.
    fileParallelism: false,
  },
});
