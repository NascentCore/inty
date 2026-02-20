# TEST_STEPS_USER_ANALYTICS_REPORTS_IMAGE_USAGE_PANEL

## 目标

验证「用户日报周报」页面在「每日/每周用量曲线」下新增「每日/每周生图用量」面板，且包含两条曲线：

1. 生图请求数
2. 生图成功数

## 前置条件

1. 评测前端可访问（`evaluation`）
2. 后端 `GET /api/v1/evaluation/user-analytics/reports` 可返回 `daily` 报告数据
3. 报告 `stats` 中存在：
   - `total_image_generation_requests`
   - `total_image_generation_success`

## 测试步骤

1. 打开「用户日报周报」页面（路由 key：`user-analytics-reports`）。
2. 保持报告类型为「日报」。
3. 观察「每日用量曲线」面板下方，确认新增「每日生图用量」面板。
4. 在「每日生图用量」面板图例中，确认存在两条曲线：
   - 生图请求数
   - 生图成功数
5. 将报告类型切换为「周报」。
6. 观察标题变为「每周生图用量」，并确认曲线仍为上述两条。

## 预期结果

1. 「每日生图用量」面板在日报模式展示，且曲线数据可渲染。
2. 「每周生图用量」面板在周报模式展示，且曲线数据可渲染。
3. 页面无报错、无白屏，原有「每日/每周用量曲线」和报告折叠区行为不受影响。
