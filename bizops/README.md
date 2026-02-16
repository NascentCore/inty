# 业务运营相关信息 - 市场推广

info@intellimate.app

<img width="2518" height="140" alt="image" src="https://github.com/user-attachments/assets/64fcc770-d58f-4ca1-96e4-98dd16a4fb6a" />

- ads.txt 作为拷贝，secretes 里有，这里只用于阅读内容
- Ads platform: ADs power browser
  - Google Ads (yxzhao6@gmail.com)
  - facebook business (yxzhao6@gmail.com)
- YouTube channel: https://www.youtube.com/@IntelliMate（转化率最好，可以长期转化）
- Facebook page: https://www.facebook.com/profile.php?id=61579913877109#
- X account: https://x.com/IntelliMate2025 (CPM 低、量大）
- 电话：+1 (925) 209 5237

## 市场推广计划

- [菲律宾市场推广计划书](./PHILIPPINES_MARKETING_PLAN.md) - 3个月验证计划，目标$10,000营收

## Firebase 数据点位信息

### 文档索引

- **[Firebase 事件列表](./Firebase%20事件列表.md)** - Firebase Analytics / Performance 事件与业务事件统一文档，包含事件名称、参数、使用位置、采样配置、用户属性、Crashlytics 键及业务价值说明，面向产品、运营、开发与数据分析
- **[Firebase 参数类型指南](./FIREBASE_PARAMETER_TYPES_GUIDE.md)** - 自定义维度、自定义指标、计算指标的区别和项目参数分类
- **[Firebase 维度分析](./FIREBASE_DIMENSIONS_ANALYSIS.md)** - 自定义维度使用情况分析和优化建议

### 核心事件说明

1. **message_send_success** - 发送消息并且服务器正确返回的事件（不区分是否触发次数限制，vip限制等）
2. **chat_started** - 第一次发送消息时触发（替换了原来的 chat_session_start）
3. **free_limit_reached** - 免费用户发送消息后，触发了接口返回次数限制的时候上报
4. **message_sent** - 点击发送后，真正触发接口发送时的打点
5. **message_send_failure** - 消息发送接口返回失败
6. **explore_page_view** - Explore 页面的开始展示
7. **APP_OPEN** - 启动 App 时触发（Firebase内置事件）
8. **SCREEN_VIEW** - 页面访问（Firebase内置事件，通过 `PageTrackingHelper.trackPageView()` 自动记录，包含 `page_source` 参数用于统计页面来源）

**注意**：
- `chat_session_end` 事件已删除。页面离开场景通过 `page_leave` 事件自动记录（包含停留时长等信息），无需额外的事件统计。
- `SCREEN_VIEW` 事件包含 `page_source` 参数，用于统计用户从哪个入口进入页面（如 VipCenterActivity、ChatActivity 等），详见 [Firebase 事件列表](./Firebase%20事件列表.md)。
