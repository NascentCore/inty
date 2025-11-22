# 业务运营相关信息 - 市场推广

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

- **[业务事件文档](./FIREBASE_BUSINESS_EVENTS.md)** - 所有业务相关事件的详细说明
- **[事件完整文档](./FIREBASE_EVENTS_DOCUMENTATION.md)** - Analytics 和 Performance 事件的完整列表
- **[Firebase 参数类型指南](./FIREBASE_PARAMETER_TYPES_GUIDE.md)** - 自定义维度、自定义指标、计算指标的区别和项目参数分类

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
- `SCREEN_VIEW` 事件包含 `page_source` 参数，用于统计用户从哪个入口进入页面（如 VipCenterActivity、ChatActivity 等），详见 [FIREBASE_BUSINESS_EVENTS.md](./FIREBASE_BUSINESS_EVENTS.md) 和 [FIREBASE_EVENTS_DOCUMENTATION.md](./FIREBASE_EVENTS_DOCUMENTATION.md)。
