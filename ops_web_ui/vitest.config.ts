/// <reference types="vitest/config" />
import { defineConfig } from "vite";

export default defineConfig({
  test: {
    // 测试文件匹配模式
    include: ["tests/**/*.{ts,tsx}"],

    // 排除依赖目录
    exclude: ["**/node_modules/**"],

    // 测试环境
    // 适用于后端代码、工具函数、API 测试
    // 可以使用 Node.js 的 fs、path、crypto 等模块
    // 没有浏览器 API（如 window、document）
    environment: "node",
  },
});
