＃ 设计

## Cursor 摘要

- 目录用途: 设计系统与跨页面 UI 组件的集中实现。
- 区域关键：
  -`theme/`: `Color`、`Type`、`Shapes`、`Theme` 等主题定义。
  - `ui/`: 通用 Compose 组件（按钮、文本框、列表项、抽屉、工具栏、Snackbar、Shimmer 等）。
  -`utils/`: Compose 工具（`ComposeUIUtils`、`ModifierExt`、`UiTools`）。
  - 其他: `AdvancedCoilConfig`（图片加载配置）、`DesignInitializer`（初始化）。
- 作用: 为应用提供一致的视觉与交互基座，降低 UI 重复实现。
