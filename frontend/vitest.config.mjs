import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
    loader: "jsx",
    include: /src\/.*\.(js|jsx)$|tests\/.*\.jsx$/,
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.js"],
    include: ["tests/**/*.test.jsx"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      include: [
        "src/components/application-mobile-card.jsx",
        "src/components/async-state.jsx",
        "src/components/rules-engine/document-result-row.jsx",
        "src/lib/formatters.js",
        "src/lib/risk-display.js",
      ],
      thresholds: {
        lines: 75,
        functions: 75,
        statements: 75,
        branches: 65,
      },
    },
  },
});
