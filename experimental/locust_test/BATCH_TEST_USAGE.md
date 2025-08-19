# 批量测试使用指南

## 概述

提供了两个自动化测试脚本来评估不同并发数下的性能表现：

1. **`batch_test.sh`** - 完整的批量测试脚本
2. **`quick_test.sh`** - 快速测试脚本

## 快速开始

### 方法1: 使用快速测试脚本 (推荐新手)

```bash
# 测试关键并发点 (10, 30, 50, 100 用户)
./quick_test.sh
```

**特点:**
- 测试4个关键并发数点
- 每个测试运行2分钟
- 实时显示关键指标
- 测试时间约5-10分钟

### 方法2: 使用完整批量测试

```bash
# 默认测试 (10, 20, 30...100 用户, 每个2分钟)
./batch_test.sh

# 自定义配置
./batch_test.sh --host http://192.168.1.100:8000 --run-time 5m --spawn-rate 2

# 自定义用户数序列
./batch_test.sh --users '5,15,25,50,75,100'
```

## 测试配置

### 默认配置
- **目标主机**: `http://localhost:8000`
- **运行时间**: 2分钟
- **用户启动速率**: 1 用户/秒
- **并发数序列**: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100

### 自定义配置选项

```bash
./batch_test.sh [选项]

选项:
  --host HOST         目标主机地址
  --run-time TIME     测试运行时间 (如: 2m, 5m, 10m)
  --spawn-rate N      用户启动速率 (用户数/秒)
  --users 'N1,N2,N3'  自定义用户数序列 (逗号分隔)
  -h, --help          显示帮助信息
```

### 使用示例

```bash
# 测试本地服务，运行5分钟
./batch_test.sh --run-time 5m

# 测试远程服务，快速启动
./batch_test.sh --host http://192.168.1.100:8000 --spawn-rate 5

# 只测试几个关键点
./batch_test.sh --users '10,50,100' --run-time 10m

# 低强度长时间测试
./batch_test.sh --users '5,10,15,20' --run-time 20m --spawn-rate 1
```

## 测试输出

### 目录结构
```
batch_test_results/
└── 20250814_143022/                 # 时间戳目录
    ├── report_10users.html          # HTML测试报告
    ├── report_20users.html
    ├── ...
    ├── results_10users_stats.csv    # CSV统计数据
    ├── results_10users_stats_history.csv  # 历史数据
    ├── test_10users.log             # 测试日志
    ├── batch_test_summary.txt       # 详细汇总
    └── performance_analysis.txt     # 性能分析报告
```

### 关键指标说明

| 指标 | 说明 | 理想值 |
|------|------|--------|
| 平均响应时间 | 所有请求的平均耗时 | < 2000ms |
| P95响应时间 | 95%请求的响应时间 | < 5000ms |
| P99响应时间 | 99%请求的响应时间 | < 8000ms |
| RPS | 每秒处理请求数 | 越高越好 |
| 成功率 | 请求成功的百分比 | > 95% |

## 结果分析

### 1. 查看实时输出
测试过程中会显示：
```
✅  10 用户 - 平均: 1245ms, P95: 2100ms, RPS: 3.2
✅  20 用户 - 平均: 1890ms, P95: 3200ms, RPS: 5.1
```

### 2. 详细HTML报告
- 打开 `report_XXusers.html` 查看详细的性能图表
- 包含响应时间分布、RPS曲线等

### 3. 性能分析报告
查看 `performance_analysis.txt` 获取：
- 性能对比表格
- 趋势分析建议
- 瓶颈识别指导

### 4. CSV数据分析
使用Excel或其他工具打开CSV文件进行深度分析：
- `results_XXusers_stats.csv` - 最终统计
- `results_XXusers_stats_history.csv` - 时间序列数据

## 性能基线建议

### 聊天接口性能目标

| 并发数 | 平均响应时间 | P95响应时间 | 最小RPS | 成功率 |
|--------|--------------|-------------|---------|--------|
| ≤ 20   | < 1500ms     | < 3000ms    | > 2.0   | > 98%  |
| 21-50  | < 2500ms     | < 5000ms    | > 3.0   | > 95%  |
| 51-100 | < 4000ms     | < 8000ms    | > 2.5   | > 90%  |

### 性能评估指标

1. **响应时间趋势**: 随并发数增长是否线性
2. **吞吐量峰值**: 在哪个并发数达到最高RPS
3. **稳定性拐点**: 成功率开始下降的并发数
4. **资源瓶颈**: P99延迟急剧上升的点

## 故障排除

### 常见问题

1. **连接失败**
   ```bash
   # 检查服务状态
   curl http://localhost:8000/health
   
   # 检查Docker服务
   docker-compose ps
   ```

2. **测试中断**
   ```bash
   # 查看具体错误日志
   cat batch_test_results/*/test_XXusers.log
   ```

3. **结果异常**
   ```bash
   # 验证locustfile.py语法
   python -m py_compile locustfile.py
   
   # 手动执行单个测试
   locust -f locustfile.py --host http://localhost:8000 --users 10 --run-time 30s --headless
   ```

### 调试模式

```bash
# 启用详细日志
export LOCUST_LOGLEVEL=DEBUG
./batch_test.sh --users '10' --run-time 1m

# 单步测试
locust -f locustfile.py --host http://localhost:8000 --users 5 --spawn-rate 1 --run-time 30s --headless -v
```

## 最佳实践

### 测试环境准备
1. 确保测试环境稳定，无其他负载
2. 使用生产环境相同的配置
3. 准备充足的测试数据

### 测试执行
1. 从小并发数开始测试
2. 观察系统资源使用情况
3. 记录测试时的环境条件

### 结果解读
1. 关注趋势而非绝对值
2. 结合系统监控数据分析
3. 多次测试取平均值

---

**提示**: 首次使用建议先运行 `./quick_test.sh` 熟悉流程，再使用完整的批量测试功能。