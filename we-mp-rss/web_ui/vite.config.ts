import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig(({ command, mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_PROXY_TARGET || env.VITE_API_BASE_URL || "http://backend:8001/";

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    // 定义 Vue 特性标志
    define: {
      __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
      __VUE_OPTIONS_API__: 'true',
      __VUE_PROD_DEVTOOLS__: 'false',
    },
    // 基础路径配置
    base: command === "serve" ? "/" : "/",
    // 开发服务器配置
    // 构建配置
    build: {
      outDir: "dist",
      emptyOutDir: true,
      assetsDir: "assets",
      // 确保资源路径使用相对路径，适合 Flutter WebView 加载
      rollupOptions: {
        output: {
          manualChunks: undefined,
        },
      },
    },
    server: {
      host: "0.0.0.0",
      port: 3000,
      proxy: {
        "/views": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/proxy": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/static": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/files": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/rss": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/feed": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
