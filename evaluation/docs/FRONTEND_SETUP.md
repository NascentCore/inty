# 🎨 前端构建和运行指南

## 📋环境要求

- **Node.js**：16.0+（推荐18.x或20.x）
- **npm**：8。0+ (或纱线/pnpm)
- **卧室服务**：InTy 卧室运行在 http://localhost:8000

## 🚀 快速开始

### 方法1：使用构建脚本（推荐）```bash
# 进入评测系统目录
cd app/static/evaluation

# 开发模式 (自动启动开发服务器)
./dev.sh

# 生产构建
./build.sh
```

### 方法2: 手动操作

```bash
# 1. 进入评测系统目录
cd app/static/evaluation

# 2. 安装依赖
npm install

# 3. 开发模式 (推荐)
npm run dev

# 4. 或生产构建
npm run build
```

## 📖 详细说明

### 🛠️ 开发模式

开发模式提供热重载、代理等功能，适合开发调试：

```bash
npm run dev
```

**特性**:

- ✅ 热重载 - 代码修改实时生效
- ✅ API代理 - `/api`请求自动代理到前端
- ✅ TypeScript 支持
- ✅ ESLint 代码检查
- ✅ 源码地图（源地图）

**访问地址**：

- 前端: http://localhost:3000
- API代理: http://localhost:3000/api → http://localhost:8000/api

### 🏗️ 生产构建

生产构建生成优化后的静态文件：```bash
npm run build
```

**输出**:

- 构建文件: `./dist/` 目录
- 入口文件: `./dist/index.html`
- 静态资源: `./dist/assets/`**优化特性**：

- ✅ 代码分割
- ✅ 资源压缩
- ✅ 摇树
- ✅ 缓存优化

### 🔍 预览构建结果```bash
npm run preview
```在 http://localhost:4173 预览构建后的应用程序

## 🗂️ 项目结构```
app/static/evaluation/
├── components/           # React 组件
│   └── evaluation/      # 评测相关组件
├── pages/               # 页面组件
├── hooks/               # React Hooks
├── services/            # API 服务
├── types/               # TypeScript 类型
├── styles/              # 样式文件
├── package.json         # 依赖配置
├── vite.config.ts       # Vite 配置
├── tsconfig.json        # TypeScript 配置
├── index.html           # HTML 模板
├── index.tsx            # 应用入口
└── dist/                # 构建输出 (构建后生成)
```

## 🔧 配置说明

### Vite 配置 (`vite.config.ts`)

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // 开发服务器端口
    proxy: {
      "/api": "http://localhost:8000", // API代理
    },
  },
  build: {
    outDir: "dist", // 构建输出目录
    sourcemap: true, // 生成源码映射
  },
});
```### TypeScript 配置 (`tsconfig.json`）

- 严格模式
- 路径别名支持
- JSX 支持
- ES2020目标

## 🚨 常见问题

### Q1：`npm install`失败

**A**：检查节点。js版本，确保是16+```bash
node --version  # 应该是 v16+ 或 v18+
```

### Q2: 开发服务器启动失败

**A**: 检查端口是否被占用

```bash
lsof -i :3000  # 检查 3000 端口
```### Q3: API 请求失败

**A**：确保临时服务运行正常```bash
curl http://localhost:8000/  # 测试后端
```

### Q4: 构建后静态文件 404

**A**: 检查构建输出和服务器配置

```bash
ls -la dist/  # 检查构建文件
```### Q5：TypeScript 错误

**A**：运行类型检查```bash
npm run type-check
```## 📊 性能优化

### 1. 代码分割

Vite自动进行代码分割，将供应商库和应用程序代码分离

### 2.资源压缩

生产构建自动压缩JS、CSS、HTML

### 3. 策略服务器

静态资源使用内容存储配置，支持长期存储

### 4.摇树

未使用的代码自动删除

## 🎯 配置选项

### 选项1: 集成到劳动力 (推荐)```bash
# 构建前端
npm run build

# 将 dist/ 内容复制到后端静态目录
cp -r dist/* ../../../static/evaluation/
```

### 选项2: 独立部署

```bash
# 使用任何静态文件服务器
npx serve dist/
# 或
python -m http.server 8080 -d dist/
```

### 选项3: CDN 部署

将 `dist/` 目录上传到 CDN 或静态站点托管服务

## 🛡️ 开发建议

1. **使用开发模式进行调试**
2. **定期运行 `npm run lint` 检查代码**
3. **提交前运行 `npm run build`确定构建成功**
4. **使用TypeScript严格模式**
5. **遵循React Hooks最佳实践**

## 📞 技术支持

遇到问题时请检查：

1. Node.js 和 npm 版本
2. 座位服务状态
3.浏览器控制台错误
4.终端错误输出

---

**🎉开始开发吧！** 足球系统扩展已配置完成，支持现代化的开发体验。