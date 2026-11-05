import { defineConfig, loadEnv } from "vite";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";

const projectRoot = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig(({ mode }) => {
  // Only VITE_ variables are exposed to client code; backend secrets stay server-side.
  const env = loadEnv(mode, projectRoot, "");
  const backendHost = env.BACKEND_HOST || env.HOST || "127.0.0.1";
  const targetHost = ["0.0.0.0", "::"].includes(backendHost)
    ? "127.0.0.1"
    : backendHost;
  const backendPort = Number(env.BACKEND_PORT || env.PORT || 8000);
  const frontendPort = Number(env.FRONTEND_PORT || 5173);
  for (const [name, port] of [
    ["BACKEND_PORT", backendPort],
    ["FRONTEND_PORT", frontendPort],
  ] as const) {
    if (!Number.isInteger(port) || port < 1 || port > 65535)
      throw new Error(
        `${name} must be an integer between 1 and 65535 in .env.`,
      );
  }
  return {
    envDir: projectRoot,
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: frontendPort,
      strictPort: true,
      proxy: {
        "/api": {
          target: `http://${targetHost.includes(":") ? `[${targetHost}]` : targetHost}:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  };
});
