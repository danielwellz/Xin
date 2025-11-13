import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const fallbackApiBase = env.VITE_API_BASE_URL ?? "http://localhost:8000";
  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": "/src"
      }
    },
    css: {
      postcss: "./postcss.config.cjs"
    },
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
      __API_BASE_URL__: JSON.stringify(fallbackApiBase)
    },
    server: {
      port: Number(env.VITE_DEV_PORT ?? 4173),
      host: "0.0.0.0",
      proxy: {
        "/admin": {
          target: fallbackApiBase,
          changeOrigin: true
        }
      }
    },
    build: {
      outDir: "dist",
      sourcemap: true
    }
  };
});
