/// <引用类型=“vitest/config”/>
import { defineConfig } from "vite";

export default defineConfig({
  test: {
// 测试文件匹配模式
    include: ["tests/**/*.{ts,tsx}"],
// 测试环境
// 适用于支架代码、工具函数、API 测试
// 可以使用Node.js的fs、path、crypto等模块
// 没有浏览器API（如窗口、文档）
    environment: "node",
  },
});
