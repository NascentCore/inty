# 恢复用户订阅脚本

## 简介

本脚本用于恢复由于前端问题导致订阅失败的用户订阅。当前脚本专门为 `bobbyjackson150@googlemail.com` 用户恢复月付会员订阅。

## 功能

- 通过邮箱查询用户
- 查找月付订阅计划（`premium_monthly`）
- 检查是否已存在订阅记录（基于购买令牌或订单 ID）
- 取消用户其他活跃订阅（如果有）
- 创建新的订阅记录（状态为 ACTIVE，时长为 1 个月，与 Google Play 月付周期一致）
- 创建对应的交易记录（PURCHASE 类型）

## 使用方法

### 前置条件

1. 确保数据库连接配置正确（通过 `app/core/config.py` 中的配置）
2. 确保用户和订阅计划已存在于数据库中

### 运行脚本

#### Dry Run 模式（推荐先运行）

在正式执行前，建议先使用 dry run 模式进行校验：

```bash
# 从项目根目录运行（dry run 模式）
python experimental/restore_subscription/restore_subscription.py --dry-run
```

或者：

```bash
# 进入脚本目录
cd experimental/restore_subscription
python restore_subscription.py --dry-run
```

Dry run 模式会：

- 执行所有查询和验证操作
- 显示将要执行的所有操作
- **不会实际修改数据库**
- 帮助你在正式执行前发现问题

#### 正式执行

确认 dry run 模式校验通过后，可以正式执行：

```bash
# 从项目根目录运行
python experimental/restore_subscription/restore_subscription.py
```

或者：

```bash
# 进入脚本目录
cd experimental/restore_subscription
python restore_subscription.py
```

### 脚本配置

脚本中的关键配置（硬编码在脚本中）：

- **用户邮箱**: `bobbyjackson150@googlemail.com`
- **购买令牌**: `bkeleepadcbbjkaanblkbfbb.AO-J1OzJtZ1UIzIVffU-aA3TpsSHMYMZZqCFIBwMRvxxcWtqnsdeuqfO8cKTPtkbJ5zk2xr5La1Jm6OKY9nT86Z-7iqDhckbAw`
- **订单 ID**: `GPA.3399-1456-6599-70500`
- **订阅计划 ID**: `premium_monthly`
- **开始时间**: `2025-11-05 17:59:28 UTC`
- **订阅时长**: 1 个月（与 Google Play 月付周期一致，避免续费时的时间覆盖问题）

## 脚本执行流程

1. **查找用户**: 通过邮箱查询用户记录
2. **查找订阅计划**: 查找月付订阅计划（`premium_monthly`）
3. **检查现有订阅**: 检查是否已存在使用相同购买令牌或订单 ID 的订阅记录
4. **取消其他订阅**: 如果用户有其他活跃订阅，将其取消
5. **创建订阅记录**: 创建新的订阅记录，状态为 ACTIVE
6. **创建交易记录**: 创建对应的购买交易记录
7. **提交事务**: 提交所有数据库更改

## 注意事项

- **建议先运行 dry run 模式**：使用 `--dry-run` 参数先进行校验，确认无误后再正式执行
- 脚本会检查是否已存在订阅记录，如果存在则不会重复创建
- 脚本会自动取消用户的其他活跃订阅
- 订阅时长为 1 个月（从开始时间计算，与 Google Play 月付周期一致）
- 自动续费设置为 `True`
- 所有操作都会记录详细的日志
- Dry run 模式下不会实际修改数据库，所有更改都会回滚

## 输出示例

### Dry Run 模式输出示例

```
============================================================
开始恢复用户订阅 [DRY RUN 模式 - 不会实际修改数据库]
============================================================
查找用户: bobbyjackson150@googlemail.com
找到用户: user_xxx (用户昵称)
查找订阅计划: premium_monthly
找到订阅计划: Monthly (价格: 9.99 USD)
检查是否已存在订阅记录...
检查并取消用户其他活跃订阅...
[DRY RUN] 创建订阅记录...
[DRY RUN] 将创建订阅记录:
  - 订阅ID: subscription_xxx
  - 用户ID: user_xxx
  - 计划ID: premium_monthly
  - 状态: ACTIVE
  - 开始时间: 2025-11-05 17:59:28+00:00
  - 结束时间: 2025-12-05 17:59:28+00:00
  - 自动续费: True
[DRY RUN] 创建交易记录...
[DRY RUN] 将创建交易记录:
  - 交易ID: transaction_xxx
  - 订阅ID: subscription_xxx
  - 用户ID: user_xxx
  - 类型: PURCHASE
  - 金额: 9.99 USD
  - 状态: COMPLETED
[DRY RUN] 将提交事务（实际不会提交）
============================================================
订阅恢复校验完成！[DRY RUN 模式 - 未实际修改数据库]
============================================================
...
```

### 正式执行输出示例

脚本执行成功后会输出：

```
============================================================
开始恢复用户订阅
============================================================
查找用户: bobbyjackson150@googlemail.com
找到用户: user_xxx (用户昵称)
查找订阅计划: premium_monthly
找到订阅计划: Monthly (价格: 9.99 USD)
检查是否已存在订阅记录...
检查并取消用户其他活跃订阅...
创建订阅记录...
创建交易记录...
============================================================
订阅恢复成功！
============================================================
用户ID: user_xxx
用户邮箱: bobbyjackson150@googlemail.com
订阅ID: subscription_xxx
订阅计划: Monthly
订阅状态: ACTIVE
开始时间: 2025-11-05 17:59:28+00:00
结束时间: 2025-12-05 17:59:28+00:00
自动续费: True
购买令牌: bkeleepadcbbjkaanblkbfbb.AO-J1OzJtZ1UIzIVffU-aA3TpsSHMYMZZqCFIBwMRvxxcWtqnsdeuqfO8cKTPtkbJ5zk2xr5La1Jm6OKY9nT86Z-7iqDhckbAw
订单ID: GPA.3399-1456-6599-70500
交易ID: transaction_xxx
============================================================
```

## 错误处理

如果脚本执行失败，会输出详细的错误信息，包括：

- 用户不存在
- 订阅计划不存在
- 数据库连接错误
- 其他异常情况

## 修改脚本以恢复其他用户

如果需要恢复其他用户的订阅，需要修改脚本中的以下常量：

```python
# 用户信息
USER_EMAIL = "用户邮箱"

# 订阅信息
PURCHASE_TOKEN = "购买令牌"
ORDER_ID = "订单ID"
PLAN_ID = "订阅计划ID"
GOOGLE_PLAY_PRODUCT_ID = "Google Play产品ID"

# 时间信息
START_DATE = datetime(年, 月, 日, 时, 分, 秒, tzinfo=timezone.utc)
SUBSCRIPTION_DURATION_MONTHS = 订阅时长（月数）
```
