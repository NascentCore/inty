# TEST_STEPS_UNIFIED_COMPANION_CORE_V2

## 目标

验证 `experimental/perpetual_agent/core_v2` 的 M0/M1 基础能力：

1. 事件幂等（重复入站不重复副作用）
2. Telegram 单消费者租约
3. scheduler 幂等执行
4. CLI 命令可运行

## 前置条件

- 在仓库根目录执行
- 使用项目虚拟环境：

```bash
source .venv/bin/activate
```

## 步骤 1：运行 core_v2 自动化测试

```bash
pytest -q experimental/perpetual_agent/test_core_v2_*.py
```

**通过标准：**

- 测试全部通过（当前应看到 `21 passed`）。

## 步骤 2：验证 admin replay 命令可运行

```bash
python -m experimental.perpetual_agent.core_v2.main admin replay --since-minutes 120 --limit 10
```

**通过标准：**

- 命令可正常执行并退出（无崩溃）。
- 若数据库已有事件，会按行输出事件信息。

## 步骤 3：验证 scheduler 一次执行模式

```bash
export COMPANION_TELEGRAM_BOT_TOKEN="dummy-token-for-local-cli-only"
python -m experimental.perpetual_agent.core_v2.main serve scheduler --once
```

**通过标准：**

- 命令可正常执行并退出。
- 在无到期动作时不报错。

## 步骤 4：验证 inbound 单消费者租约（建议用自动化测试）

自动化覆盖：

```bash
pytest -q experimental/perpetual_agent/test_core_v2_cli.py::test_serve_inbound_requires_single_consumer_lease
```

**通过标准：**

- 测试通过，证明已有 lease 时第二个 inbound consumer 无法启动。

## 备注

- `serve inbound` 需要真实 Telegram token 才能进行真实 long polling。
- 当前文档重点提供 M0/M1 底座的本地可重复验证步骤。
