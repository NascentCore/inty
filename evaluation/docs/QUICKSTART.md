# 🚀 InTy 足球系统快速入门指南

## 当前状态

✅ **搅拌机集成完成** - 体育系统已完全集成到 InTy 搅拌机  
✅ **API 端点已** - 所有体育API已实现并注册  
✅ **数据模型完整** - 数据库模型和迁移文件已创建  
✅ **现有API集成** - 复用现有的聊天和智能体API  
⚠️ **前端需构建** - React/TypeScript代码需要构建脚本运行

## 🔧立即开始

### 1.启动服务```bash
# 在项目根目录执行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```### 2.访问测试页面

浏览器访问：**http://localhost:8000/static/evaluation/simple.html**

该页面提供：

- ✅ API 改变性测试
- ✅ 完整的 API 文档链接
- ✅ 开发指导信息

### 3.测试API功能```bash
# 测试智能体API
curl http://localhost:8000/api/v1/ai/agents/

# 测试评测API
curl http://localhost:8000/api/v1/evaluation/sessions

# 完整API测试
python app/static/evaluation/test_integration.py
```## 📖 重要链接

- **🎮测试页面**：http://localhost:8000/static/evaluation/simple.html
- **📖 API 文档**：http://localhost:8000/docs
- **❤️健康检查**：http://localhost:8000/
- **📚完整文档**：[README.md](./README.md)

## 🎯核心特性验证

1.**✅ 使用现有聊天API** - 体育系统调用`/api/v1/chats/agents/{id}/chat/completions`
2. **✅ 使用现有智能体API** - 调用 `/api/v1/ai/agents/`3. **✅ 完整足球流程** -创建会话 → 选择智能体 → 执行足球 → 查看结果
4. **✅ 实时监控** - WebSocket 监控气压详细资料
5.**✅自动评分** - LLM 自动评分系统

## 🎨 前端部署和运行

当前前端是完整的React + TypeScript代码，支持现代化开发：

### 快速启动 (推荐)```bash
cd app/static/evaluation

# 交互式演示脚本
./demo.sh

# 或直接启动开发模式
./dev.sh
```**⚡立即访问**：http://localhost:3000

**🔧当前状态**：

- ✅ API路径重复问题已彻底修复
- ✅前端开发服务器运行正常(http://localhost:3000)
- ✅ 前端API代理连接正常 (/api → http://localhost:8000/api)
- ✅所有体育API端点工作正常
- ✅前端热重载功能正常
- ✅ 自动游客认证系统集成完毕
- ✅ 防重复API调用机制已实现
- ✅ 所有功能现已完全可用且稳定

### 手动构建```bash
cd app/static/evaluation

# 安装依赖
npm install

# 开发模式 (热重载)
npm run dev    # http://localhost:3000

# 生产构建
npm run build  # 输出到 dist/

# 预览构建结果
npm run preview  # http://localhost:4173
```### 环境要求

- Node.js 16+ (当前: $(node --version))
- npm 8+ (当前: $(npm --version))

详细说明请查看：[FRONTEND_SETUP.md](./FRONTEND_SETUP.md)

## 🔐 认证配置

赌场系统使用**自动游客认证**，消耗手动配置令牌：

###自动认证流程

1. **首次访问**：接口自动创建游客用户并获取token
2. **后续使用**：token自动保存在localStorage中，持续使用
3.**侧边栏显示**：可查看当前认证状态和用户ID

### 手动测试认证```bash
# 测试游客认证API
curl -X POST http://localhost:8000/api/v1/auth/guest \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "system_language": "zh-CN", "age_group": "adult"}'

# 使用返回的token测试API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/evaluation/sessions
```

### 认证测试页面

- **测试页面**: http://localhost:8000/static/evaluation/test-auth.html
- **功能**: 手动测试游客认证和API调用

**注意**: 评测系统专为测试设计，使用游客模式即可访问所有功能，无需注册或登录。

## 🆘 故障排除

### 问题1: 404 - 找不到页面

**解决**: 确保访问 `/static/evaluation/simple.html` 而不是 `/static/evaluation/index.html`

### 问题2: API 调用失败

**解决**: 检查后端服务是否正常运行在 8000 端口

### 问题3: 数据库错误

**解决**: 运行 `alembic upgrade head` 进行数据库迁移

### 问题4: 智能体列表为空

**解决**: 确保数据库中有智能体数据，或先创建一些测试智能体

## 📞 技术支持

如有问题，请检查：

1. 后端服务日志
2. 浏览器控制台错误
3. API 文档 (http://localhost:8000/docs)
4. 完整文档 (README.md)

---

**🎉 恭喜！** InTy 评测系统已成功集成！现在可以使用现有的聊天基础设施进行智能体评测了。
