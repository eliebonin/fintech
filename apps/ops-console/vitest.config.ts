import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const directory = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  test: {include:['src/**/*.test.{ts,tsx}']},
  resolve: {
    alias: { "@": path.join(directory, "src") },
  },
});
