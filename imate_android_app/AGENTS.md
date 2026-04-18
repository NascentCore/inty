---
description: 
alwaysApply: true
---

---
description: 
alwaysApply: true
---

# Agentic AI companion App on Android

- [开发计划](/docs/FR_IMATE_DEVELOPMENT_PLAN.md)
- 用户可见变更与用户向说明：[docs/CHANGE_LOGS.md](docs/CHANGE_LOGS.md)、[docs/USER_MANUAL.md](docs/USER_MANUAL.md)（维护方式对齐 `android_app/docs/CHANGE_LOGS.md` 与根目录 `docs/INTELLIMATE.md`）

# UI实现原则
- 尽量避免自定义颜色、字体和形状，而是通过标准Material3获取
- 如果设计稿使用了项目不存在的颜色，可以在core/com/ai/core/ui/theme/Color新增定义，但需要明确告知该项操作
