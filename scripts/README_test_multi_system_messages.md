# 多System Message测试脚本使用说明

## 概述
`test_multi_system_messages.py` 是一个测试脚本，用于验证OpenAI兼容的chat接口是否正确支持多个system message。

## 功能特性
- ✅ 测试单个vs多个system message的效果对比
- ✅ 验证不同顺序的system message是否影响响应
- ✅ 测试包含空system message的容错处理
- ✅ 详细的结果分析和报告
- ✅ 自动保存测试结果到JSON文件

## 测试场景
脚本包含以下4个测试用例：

1. **单个System Message** - 将所有指令合并为一个system message（对照组）
2. **多个System Message** - 分别设置主提示词、角色信息、用户信息
3. **不同顺序** - 测试system message顺序对效果的影响  
4. **包含空消息** - 测试系统对空system message的处理

## 使用方法

### 基本使用
```bash
# 使用默认配置文件
python scripts/test_multi_system_messages.py

# 或者直接执行
./scripts/test_multi_system_messages.py
```

### 高级选项
```bash
# 指定配置文件
python scripts/test_multi_system_messages.py --config /path/to/config.yaml

# 指定输出文件名
python scripts/test_multi_system_messages.py --output my_test_results.json

# 查看帮助
python scripts/test_multi_system_messages.py --help
```

## 依赖要求
确保已安装必要的依赖：
```bash
pip install openai pyyaml
```

## 配置文件
脚本会自动读取项目根目录的 `config.yaml` 文件中的agent配置：
```yaml
agent:
  api_key: your_api_key
  base_url: https://your-api-endpoint/v1
  model: your_model_name
```

## 输出说明

### 控制台输出
- 实时显示测试进度和状态
- 显示每个测试的成功/失败状态
- 分析响应内容和关键词匹配
- 提供测试结论和建议

### JSON结果文件
包含详细的测试数据：
- 每个测试的完整请求和响应
- 响应时间和API使用统计
- 错误信息（如有）
- 时间戳和元数据

## 结果分析
脚本会自动分析：
- ✅ 响应内容是否包含预期关键词
- ✅ 不同测试方式的响应差异
- ✅ API调用性能统计
- ✅ 多个system message的生效情况

## 示例输出
```
🚀 开始多System Message测试
✅ OpenAI客户端初始化成功
🔄 执行测试: single_system
✅ 测试成功 - 耗时: 2.34秒
🔄 执行测试: multi_system  
✅ 测试成功 - 耗时: 2.18秒
...

📊 测试结果分析
总测试数: 4
成功: 4 ✅
失败: 0 ❌

🎯 测试结论
✅ 单个System Message测试成功
✅ 多个System Message测试成功
```

## 故障排除
1. **API调用失败** - 检查API密钥和网络连接
2. **配置文件错误** - 确保config.yaml格式正确
3. **依赖缺失** - 运行 `pip install openai pyyaml`
4. **权限问题** - 确保脚本有执行权限

## 注意事项
- 脚本会在测试间添加1秒延迟，避免API限制
- 建议在测试环境中运行，避免影响生产配额
- 测试结果会自动保存，便于后续分析