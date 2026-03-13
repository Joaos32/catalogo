import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const proxyTarget = env.VITE_DEV_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/catalog": {
          target: proxyTarget,
          changeOrigin: true,
        },
        "/auth": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
