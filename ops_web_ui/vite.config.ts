import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";
import { fileURLToPath, URL } from "node:url";

// https://vitejs.dev/config/
export default defineConfig(() => {
  const __dirname = fileURLToPath(new URL(".", import.meta.url));

  return {
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
          // 启用 WebSocket 代理
          ws: true,
          // 确保所有 headers 都被正确传递（包括 Authorization）
          // Vite 默认会传递所有 headers，但为了确保，我们显式配置
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
  };
});
