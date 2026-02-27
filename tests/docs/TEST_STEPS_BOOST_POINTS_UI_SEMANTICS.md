<!-- CREATED_BY_AGENT -->
## 目标

验证 Hype iMate 功能相关的三类数值在 UI 中**不再混淆**，并且在「不可用态」下依然可点开解释与引导。

## 前置条件

- 具备可登录账号或游客模式可进入应用主流程
- 网络可用（用于 Top 10 拉取后端 `energy_points` 排行）

## 用例 1：聊天页不再展示“iMate 聊天 pts”

- **步骤**：进入任一 iMate 聊天页（Chat）
- **期望**：
  - 顶部栏不再显示 `⚡ xx pts`（避免与 Hype Credits / iMate Hype Score 混淆）
  - 仍可点击顶部栏进入 iMate 详情页

## 用例 2：Hype Credits（账号可支配）在 <100 时可点开解释

- **步骤**：在「签到页 / 排行榜页 / iMate 详情页」看到 `Hype Credits` 卡片，且 points < 100
- **期望**：
  - 卡片显示灰态，但**可点击**
  - 点击后弹出说明面板：
    - 解释 Hype Credits 的用途（先获得，再选择 Hype 哪个 iMate）
    - 展示 `当前 / 100` 的进度
    - 提供进入 `Top 10` 的入口

## 用例 3：iMate 详情页同时展示两类指标（账号 vs iMate）

- **步骤**：从聊天页进入 iMate 详情页（Agent Info）
- **期望**：
  - 显示 `Hype Credits`（账号可支配）
  - 显示 `iMate Hype Score: N`（iMate 榜单总分）与解释文案
  - 提供 `View Top 10` 跳转入口

## 用例 4：Hype 弹窗解释“Hype 的结果”

- **步骤**：在 iMate 详情页点 `Hype`（或从榜单点 Hype 进入聊天后弹出）
- **期望**：
  - 弹窗内显示该 iMate `iMate Hype Score` 与解释（用于榜单排序）
  - 能跳转 `Top 10` 查看榜单
  - Hype 成功后，返回聊天/详情页流程不中断

