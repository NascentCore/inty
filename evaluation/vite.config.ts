import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // 设置基础路径，用于部署到子路径
  // Vite 在构建时将所有资源路径都加上 /evaluation/ 前缀。
  // 构建前：
  // <script src="/assets/main.js"></script>
  // 构建后：
  // <script src="/evaluation/assets/main.js"></script>
  // 构建前：
  // background-image: url('/images/logo.png');
  // 构建后：
  // background-image: url('/evaluation/images/logo.png');
  base: "/evaluation/",

  // 依赖优化配置
  optimizeDeps: {
    // 包含 inty 包进行优化
    include: ['inty'],
  },

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
});
