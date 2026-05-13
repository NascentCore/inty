# TEST_STEPS_USER_ANALYTICS_DAILY_REPORT_GENERATED_IMAGES

## 测试范围

验证每日日报生成时会保存“指定日期的生图列表”，并且每日日报页面能正确展示缩略图、模型信息与图片详情 metadata。

## 前置条件

1. 后端以测试配置启动。
2. 目标日期至少存在 1 条 `chat_history` 记录满足：
   - `meta_data.generated_image.image_url` 非空
   - `deleted_at` 为空
3. 可访问 evaluation 前端页面。

## 测试步骤

1. 对指定日期强制重算日报：
   - `python tools/scripts/run_user_analytics_report.py --type daily --date 2026-02-01 --force`
2. 打开页面：`用户日报周报`。
3. 选择 `报告类型 = 日报`。
4. 展开 `2026-02-01` 这一项日报。
5. 查看卡片：`当天生成图片（N）`。
6. 确认可见图片缩略图列表。
7. 确认每个缩略图下方显示 `模型: ...`（有值或显示 `未知模型`）。
8. 点击任意缩略图，弹出 `图片详情`。
9. 在弹窗内确认：
   - 显示模型、提示词、生成时间等基础信息；
   - 若 metadata 含多参考图（角色参考图 + 用户参考图），两者都可见；
   - 显示 `完整 metadata` JSON 区域。
10. 确认图片 URL 为 Web 地址（不是 `gs://`）。

## 预期结果

1. 日报 JSON 中存在 `charts.generated_images` 且为数组。
2. 页面显示 `当天生成图片（N）` 卡片。
3. 缩略图下方显示模型信息。
4. 缩略图可点击并打开图片详情弹窗。
5. 弹窗可查看完整 metadata。
6. 当天无数据时显示 `当天无生图`。
