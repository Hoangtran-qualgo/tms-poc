import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    // Python differential cases start one watcher per fixture root; running
    // files serially avoids host-level FSEvents contention in local runs.
    fileParallelism: false,
  },
});
