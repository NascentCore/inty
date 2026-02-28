<!-- CREATED_BY_AGENT -->
## 目标

验证 Free 用户可以通过 **Daily Check-in** 与 **Invite Friends** 获得额外聊天额度（Bonus Chats），并在聊天触达上限时被正确消耗与引导。

## 前置条件

- Android App 已接入 `free-quota` 相关接口
- 测试账号 2 个：`inviter_user`、`invitee_user`
- 两台设备（或模拟器）用于验证邀请链路，避免同设备风控误判
- 后端可访问，并可查看相关日志/数据库记录

## 用例 1：签到领取 Bonus Chats（Free 用户）

- **步骤**
  1. 使用 Free 账号登录，进入 `Me -> Daily Check-in`
  2. 点击签到按钮
  3. 返回聊天页查看额度展示
- **期望**
  - 签到成功提示包含 `+N Bonus Chats`
  - 当日再次签到提示已领取，不重复加额
  - `bonus_chat_quota` 余额增加，且与服务端一致

## 用例 2：聊天额度消耗顺序

- **步骤**
  1. 准备账号：`base_daily_chat_limit` 接近用尽，且有 `bonus_chat_quota > 0`
  2. 连续发送消息直到触发消耗
  3. 观察服务端返回和客户端展示
- **期望**
  - 优先消耗 `base_daily_chat_limit`
  - base 用尽后自动消耗 `bonus_chat_quota`
  - `bonus_chat_quota` 用尽前不出现订阅限制弹窗

## 用例 3：限额弹窗三路径引导

- **步骤**
  1. 构造账号：`base_daily_chat_limit=0` 且 `bonus_chat_quota=0`
  2. 在聊天页继续发送消息，触发限额弹窗
  3. 依次点击 `Go Premium`、`Daily Check-in`、`Invite Friends`
- **期望**
  - 弹窗展示三类 CTA
  - `Daily Check-in` 能跳转签到页
  - `Invite Friends` 能跳转邀请页
  - `Go Premium` 保持现有订阅跳转逻辑

## 用例 4：邀请成功发奖（正向）

- **步骤**
  1. `inviter_user` 在邀请页生成并分享邀请码
  2. `invitee_user` 使用该链接安装/打开 App，完成注册登录
  3. `invitee_user` 完成首聊激活动作
  4. 回到 `inviter_user` 检查奖励状态
- **期望**
  - `invitee_user` 获得欢迎 Bonus Chats（若策略开启）
  - `inviter_user` 获得邀请奖励 Bonus Chats
  - 事件埋点与奖励流水记录完整

## 用例 5：邀请风控拦截（负向）

- **步骤**
  1. 同设备重复注册/切号执行邀请激活
  2. 或构造明显异常行为（超速批量激活）
- **期望**
  - 奖励不发放或进入 pending/rejected 状态
  - 客户端有可见状态提示，不出现静默失败
  - 服务端风控日志可追踪

## 用例 6：灰度开关验证

- **步骤**
  1. 关闭 `enable_free_quota_invite_bonus`
  2. 重新进入 App 相关页面
  3. 再打开开关并刷新
- **期望**
  - 关闭时 Invite 入口/奖励相关 UI 不展示或不可用
  - 开启后恢复显示并可执行流程

