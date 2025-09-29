# API Endpoint Environment Control

本文档描述了如何控制API endpoints在不同环境中的可见性和可用性。

## 概述

为了确保生产环境的安全性，某些API endpoints不应该在生产环境中暴露。本系统提供了多种机制来控制endpoints的环境可见性：

1. **中间件过滤** - 在请求级别过滤endpoints
2. **装饰器控制** - 在函数级别控制endpoints
3. **路由过滤** - 在路由注册时过滤endpoints
4. **配置管理** - 集中管理endpoint配置

## 被屏蔽的Endpoints

### 生产环境屏蔽的Endpoints

以下endpoints在生产环境(`prod`)中会被自动屏蔽：

- `/api/v1/evaluation/*` - 评测系统API
- `/api/v1/admin/*` - 管理员API
- `/api/v1/report/` - 举报查询API (GET方法，管理员功能)

### 允许的Endpoints

以下endpoints在所有环境中都可用：

- `/api/v1/auth/*` - 认证相关API
- `/api/v1/users/*` - 用户管理API
- `/api/v1/chat/*` - 聊天相关API
- `/api/v1/agents/*` - 智能体管理API
- `/api/v1/report` - 举报提交API (POST方法，用户功能)

## 使用方法

### 1. 中间件过滤

中间件会自动过滤生产环境中的受限endpoints：

```python
# 在 main.py 中已配置
app.add_middleware(
    create_endpoint_filter_middleware,
    restricted_endpoints=None  # 使用默认配置
)
```

### 2. 装饰器控制

使用装饰器来控制特定endpoint的环境可见性：

```python
from app.api.decorators.environment_control import production_hidden, dev_only, non_production_only

# 在生产环境中隐藏
@production_hidden
async def admin_endpoint():
    return {"message": "Admin only"}

# 仅在开发环境中可用
@dev_only
async def debug_endpoint():
    return {"message": "Debug info"}

# 在非生产环境中可用
@non_production_only
async def test_endpoint():
    return {"message": "Test only"}
```

### 3. 路由过滤

在路由注册时应用环境控制：

```python
from app.api.utils.route_filter import get_environment_controlled_router

# 应用环境控制
evaluation_router = get_environment_controlled_router(evaluation.router)
api_router.include_router(evaluation_router)
```

### 4. 配置管理

在 `app/core/endpoint_config.py` 中管理endpoint配置：

```python
# 添加新的生产环境屏蔽endpoint
endpoint_config.production_hidden_prefixes.add("/api/v1/new-admin")

# 添加特定的屏蔽路由
endpoint_config.production_hidden_routes.add("/api/v1/specific-endpoint")
```

## 环境配置

系统通过 `config.yaml` 中的 `app.environment` 配置来识别当前环境：

```yaml
app:
  environment: "prod"  # 或 "dev", "staging"
```

## 测试

运行测试来验证endpoint过滤功能：

```bash
pytest tests/test_endpoint_filtering.py -v
```

## 安全考虑

1. **生产环境隔离** - 确保敏感的管理和调试功能不会在生产环境中暴露
2. **配置集中化** - 所有endpoint配置集中管理，便于维护
3. **多层防护** - 使用中间件、装饰器和路由过滤的多层防护机制
4. **日志记录** - 所有被屏蔽的请求都会记录日志

## 故障排除

### 常见问题

1. **Endpoint意外被屏蔽**
   - 检查 `app/core/endpoint_config.py` 中的配置
   - 确认当前环境设置正确

2. **Endpoint应该被屏蔽但没有被屏蔽**
   - 检查中间件是否正确注册
   - 确认路径匹配规则正确

3. **装饰器不生效**
   - 确认装饰器正确应用
   - 检查环境变量设置

### 调试模式

在开发环境中，可以通过日志查看endpoint过滤的详细信息：

```python
import logging
logging.getLogger("app.api.middleware.endpoint_filter").setLevel(logging.DEBUG)
```

## 扩展

### 添加新的环境控制

1. 在 `endpoint_config.py` 中添加新的配置
2. 在 `endpoint_filter.py` 中添加相应的逻辑
3. 更新测试用例
4. 更新文档

### 自定义装饰器

可以创建自定义的环境控制装饰器：

```python
from app.api.decorators.environment_control import environment_controlled

@environment_controlled(allowed_environments=["staging", "prod"])
async def staging_and_prod_endpoint():
    return {"message": "Staging and production only"}
```
