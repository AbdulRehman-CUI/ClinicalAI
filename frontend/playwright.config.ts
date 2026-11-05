import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  timeout: 90_000,
  workers: 2,
  reporter: "list",
  use: {
    baseURL,
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
      : {},
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${new URL(baseURL).port}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
  },
});
