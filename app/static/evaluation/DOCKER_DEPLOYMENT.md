# 🐳 Docker 部署指南

## 🚀 快速开始

### 方法1: 使用构建脚本（推荐）

```bash
# 构建并运行
./docker-build.sh

# 指定版本和端口
./docker-build.sh v1.0.0 3000
```

### 方法2: 手动操作

```bash
# 构建镜像
docker build -t inty-evaluation-frontend:latest .

# 运行容器
docker run -d \
  --name inty-frontend \
  -p 3000:80 \
  --restart unless-stopped \
  inty-evaluation-frontend:latest
```

### 方法3: 使用 Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 📁 项目结构

```
app/static/evaluation/
├── Dockerfile              # 标准 Docker 配置
├── Dockerfile.prod         # 生产环境优化版
├── docker-compose.yml      # Docker Compose 配置
├── .dockerignore          # Docker 忽略文件
├── nginx.conf             # Nginx 配置
├── docker-build.sh        # 构建脚本
└── k8s-deployment.yaml    # Kubernetes 部署配置
```

## 🔧 配置选项

### 环境变量

在构建时会读取 `.env.production` 文件：

```bash
REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1
```

### 端口配置

- **容器内端口**: 80 (Nginx)
- **主机端口**: 3000 (可自定义)

### 资源限制

```yaml
resources:
  requests:
    memory: "64Mi"
    cpu: "50m"
  limits:
    memory: "128Mi" 
    cpu: "100m"
```

## 🏗️ 构建优化

### 多阶段构建

1. **构建阶段**: Node.js 18 Alpine
   - 安装依赖
   - 编译 TypeScript
   - 构建生产版本

2. **运行阶段**: Nginx Alpine
   - 复制静态文件
   - 配置 Nginx
   - 安全优化

### 镜像优化

- 使用 Alpine Linux (更小的镜像)
- 多阶段构建 (减少最终镜像大小)
- .dockerignore (排除不必要文件)
- 非 root 用户运行 (安全性)

## 🔍 健康检查

```bash
# 容器健康状态
docker ps

# 健康检查端点
curl http://localhost:3000/health

# 查看健康检查日志
docker inspect inty-frontend | grep Health -A 10
```

## 📊 监控和日志

### 查看日志

```bash
# 查看容器日志
docker logs inty-frontend

# 实时日志
docker logs -f inty-frontend

# 最近 100 行日志
docker logs --tail 100 inty-frontend
```

### 监控指标

```bash
# 容器资源使用
docker stats inty-frontend

# 容器详细信息
docker inspect inty-frontend
```

## 🚀 部署选项

### 1. 单容器部署

```bash
docker run -d \
  --name inty-frontend \
  -p 3000:80 \
  --restart unless-stopped \
  inty-evaluation-frontend:latest
```

### 2. Docker Compose

```bash
# 启动
docker-compose up -d

# 扩容
docker-compose up -d --scale inty-frontend=3
```

### 3. Kubernetes

```bash
# 部署到 K8s
kubectl apply -f k8s-deployment.yaml

# 查看状态
kubectl get pods,svc,ingress
```

### 4. Docker Swarm

```bash
# 初始化 Swarm
docker swarm init

# 部署服务
docker stack deploy -c docker-compose.yml inty-stack
```

## 🔧 Nginx 配置

### 主要特性

- **Gzip 压缩**: 减少传输大小
- **静态资源缓存**: 1年缓存期
- **SPA 路由支持**: History API 路由
- **安全头**: XSS 保护等
- **健康检查**: `/health` 端点

### 自定义配置

修改 `nginx.conf` 后重新构建镜像：

```bash
docker build -t inty-evaluation-frontend:latest .
```

## 🛡️ 安全最佳实践

1. **非 root 用户运行**
2. **最小权限原则**
3. **安全头配置**
4. **敏感文件保护**
5. **定期更新基础镜像**

## 🔄 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Build and Deploy
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t inty-frontend .
      - name: Push to registry
        run: docker push your-registry/inty-frontend
```

## 🚨 故障排除

### 常见问题

1. **容器无法启动**

   ```bash
   docker logs inty-frontend
   ```

2. **端口被占用**

   ```bash
   lsof -i :3000
   docker run -p 3001:80 ...
   ```

3. **镜像构建失败**

   ```bash
   docker build --no-cache -t inty-frontend .
   ```

4. **健康检查失败**

   ```bash
   docker exec -it inty-frontend curl localhost/health
   ```

### 性能优化

1. **启用 Gzip 压缩**
2. **配置静态资源缓存**
3. **使用 CDN**
4. **监控资源使用**

## 📞 支持

遇到问题时请检查：

1. Docker 版本兼容性
2. 端口占用情况
3. 容器日志信息
4. 网络连接状态
5. 资源使用情况

---

**🎉 现在你可以使用 Docker 轻松部署 InTy 评测系统前端了！**
