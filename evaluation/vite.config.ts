import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // 构建配置
  build: {
    outDir: "dist",
    assetsDir: "assets",
    sourcemap: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
      },
      output: {
        manualChunks: {
          vendor: ["react", "react-dom"],
          antd: ["antd", "@ant-design/icons"],
        },
      },
    },
  },

  // 开发服务器配置
  server: {
    port: 3000,
    host: true,
    proxy: {
      // 代理API请求到后端
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },

  // 路径别名
  resolve: {
    alias: {
      "@": resolve(__dirname, "./"),
      "@components": resolve(__dirname, "./components"),
      "@pages": resolve(__dirname, "./pages"),
      "@hooks": resolve(__dirname, "./hooks"),
      "@services": resolve(__dirname, "./services"),
      "@types": resolve(__dirname, "./types"),
      "@styles": resolve(__dirname, "./styles"),
    },
  },

  // 环境变量
  define: {
    __DEV__: JSON.stringify(process.env.NODE_ENV === "development"),
    "process.env.REACT_APP_API_BASE_URL": JSON.stringify(
      process.env.REACT_APP_API_BASE_URL,
    ),
  },
});
