＃ 应用程序

## Cursor 摘要

- 目录用途：Android应用主模块，包含应用入口、主要页面与业务视图层。
- 区域关键：
  - 入口与全局：`IntelliMateApp`（应用），`MainActivity`、`MainViewModel`、`HomeScreen`。
  - 功能页面: 聊天（`chat/*`）、探索（`explore/*`）、角色（`agent/*`）、资料/设置（`profile/*`、`settings/*`）、VIP/订阅（`vip/*`）。
  - UI 组件: `ui/components/*` 与常用 `ui/*` 控件。
  - 音频/TTS: `audio/*`（播放、缓存、预加载、TTS 管理）。
  - 登录/注册: `login/*` 与注册信息。
  - 分页: `paging/*` 与仓库。
- 关联: 依赖 `core/*`、`library/*` 能力，通过 `core/data` 与后端交互。
