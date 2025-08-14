# Inty Backend Chat 接口并发测试计划

## 1. 测试概述

### 测试目标
- 评估Inty Backend chat接口在1c2g资源限制下的并发性能表现
- 识别系统性能瓶颈和限制
- 为生产环境容量规划提供数据支撑
- 验证系统在高并发场景下的稳定性

### 测试范围
- **主要接口**: Chat completions API (`/api/v1/chats/agents/{agent_id}/chat/completions`)
- **辅助接口**: 游客注册API (`/api/v1/auth/guest`)
- **资源限制**: 后端容器1c2g，测试环境4c8g VM

## 2. 测试环境

### 基础设施
```
Google Cloud Platform VM
├── 配置: 4核CPU + 8GB内存
├── 操作系统: Ubuntu 22.04 LTS
├── Docker Engine: 最新稳定版
└── 网络: 外网IP，防火墙开放8000端口
```

### 容器配置
```yaml
# 后端服务容器资源限制
services:
  inty-backend:
    image: inty-backend:test
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
```

### 测试工具
- **Locust**: 负载测试框架
- **Docker**: 容器化部署
- **PostgreSQL**: 数据库服务
- **监控**: htop, docker stats

## 3. 测试场景设计

### 场景1: 基础负载测试
```
目标: 评估系统基本处理能力
用户数: 5 → 20 (每30秒增加5个用户)
持续时间: 10分钟
预期: 响应时间 < 2秒，成功率 > 95%
```

### 场景2: 压力测试
```
目标: 找到系统性能拐点
用户数: 20 → 100 (每60秒增加20个用户)
持续时间: 15分钟
预期: 识别性能下降点
```

### 场景3: 峰值测试
```
目标: 测试系统峰值承载能力
用户数: 100 → 200 (快速增长)
持续时间: 5分钟
预期: 验证系统极限表现
```

### 场景4: 稳定性测试
```
目标: 验证系统长期稳定性
用户数: 50 (恒定)
持续时间: 30分钟
预期: 无内存泄漏，性能稳定
```

## 4. 测试用例

### 用例1: 用户注册流程
```python
# 模拟用户注册
def register_guest(self):
    response = self.client.post("/api/v1/auth/guest", json={
        "device_id": f"test_device_{random.randint(1000, 9999)}",
        "nickname": f"TestUser_{random.randint(100, 999)}"
    })
    return response.json()["data"]["token"]
```

### 用例2: 聊天对话
```python
# 模拟聊天请求
def chat_with_agent(self, token, agent_id):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "messages": [{"role": "user", "content": "你好，请介绍一下自己"}],
        "stream": False,
        "model": "chatbot",
        "language": "zh"
    }
    response = self.client.post(
        f"/api/v1/chats/agents/{agent_id}/chat/completions",
        json=payload,
        headers=headers
    )
```

## 5. 性能指标

### 响应时间指标
- **平均响应时间**: 所有请求的平均耗时
- **P50响应时间**: 50%请求的响应时间
- **P95响应时间**: 95%请求的响应时间
- **P99响应时间**: 99%请求的响应时间
- **最大响应时间**: 最慢请求的响应时间

### 吞吐量指标
- **RPS (Requests Per Second)**: 每秒处理请求数
- **TPS (Transactions Per Second)**: 每秒处理事务数
- **并发用户数**: 同时在线的活跃用户数

### 错误率指标
- **成功率**: 成功请求占总请求的百分比
- **错误率**: 各类错误响应的分布
- **超时率**: 请求超时的百分比

### 资源使用指标
- **CPU使用率**: 容器CPU使用百分比
- **内存使用率**: 容器内存使用情况
- **网络I/O**: 网络流量统计
- **数据库连接数**: PostgreSQL连接池状态

## 6. 监控和数据收集

### 应用层监控
```bash
# Docker容器资源监控
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" --no-stream

# 应用日志监控
docker logs -f inty-backend | grep -E "(ERROR|WARNING|Chat.*completed)"
```

### 系统层监控
```bash
# 系统资源监控
htop
iostat -x 1
free -h
df -h
```

### 数据库监控
```sql
-- PostgreSQL连接数查询
SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';

-- 查询性能分析
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

## 7. 预期结果和评估标准

### 性能基线
```
正常负载 (≤20并发):
- 平均响应时间: < 1.5秒
- P95响应时间: < 3秒
- 成功率: > 98%
- CPU使用率: < 70%
- 内存使用率: < 1.5GB

压力负载 (20-100并发):
- 平均响应时间: < 3秒
- P95响应时间: < 8秒
- 成功率: > 90%
- CPU使用率: < 90%
- 内存使用率: < 1.8GB
```

### 告警阈值
```
严重性能问题:
- 平均响应时间 > 10秒
- 成功率 < 80%
- CPU使用率 > 95%
- 内存使用率 > 1.9GB
- 错误率 > 20%
```

## 8. 风险评估和缓解措施

### 潜在风险
1. **数据库连接池耗尽**: 高并发可能导致连接数超限
2. **内存泄漏**: 长时间运行可能导致内存不足
3. **AI模型响应慢**: 外部AI服务可能成为瓶颈
4. **网络超时**: 高并发下网络可能不稳定

### 缓解措施
1. **监控数据库连接**: 实时监控连接池状态
2. **设置测试时间限制**: 避免过长的测试时间
3. **模拟AI响应**: 可考虑mock AI服务进行纯后端测试
4. **渐进式加压**: 逐步增加负载，避免突然冲击

## 9. 测试执行计划

### 阶段1: 环境准备 (预计1小时)
1. 创建GCP VM实例
2. 安装Docker和必要工具
3. 构建和部署应用容器
4. 验证基础功能

### 阶段2: 基础测试 (预计30分钟)
1. 执行场景1基础负载测试
2. 收集基线性能数据
3. 验证监控和日志收集

### 阶段3: 压力测试 (预计45分钟)
1. 执行场景2压力测试
2. 识别性能拐点
3. 记录资源使用峰值

### 阶段4: 极限测试 (预计20分钟)
1. 执行场景3峰值测试
2. 测试系统极限承载能力
3. 观察故障模式

### 阶段5: 稳定性测试 (预计30分钟)
1. 执行场景4稳定性测试
2. 验证长期运行稳定性
3. 检查内存泄漏情况

### 阶段6: 结果分析 (预计30分钟)
1. 汇总所有测试数据
2. 生成性能报告
3. 提出优化建议

## 10. 报告输出

### 测试报告结构
```
1. 执行摘要
   - 测试概述
   - 主要发现
   - 关键指标

2. 详细结果
   - 各场景测试数据
   - 性能图表
   - 错误分析

3. 系统资源分析
   - CPU/内存使用趋势
   - 数据库性能
   - 网络状况

4. 问题和建议
   - 发现的性能问题
   - 优化建议
   - 生产环境建议

5. 附录
   - 测试环境详细信息
   - 原始数据
   - 配置文件
```

### 交付物清单
- [ ] 测试执行报告 (PDF/HTML)
- [ ] 性能数据文件 (CSV)
- [ ] 测试脚本和配置
- [ ] 监控截图和日志
- [ ] 优化建议文档

---

**注意事项**:
1. 测试期间请避免其他重负载操作
2. 确保测试环境网络稳定
3. 及时保存测试数据和日志
4. 如遇严重性能问题，立即停止测试