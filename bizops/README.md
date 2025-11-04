# 业务运营相关信息 - 市场推广

- Ads platform: ADs power browser
  - Google Ads (yxzhao6@gmail.com)
  - facebook business (yxzhao6@gmail.com)
- YouTube channel: https://www.youtube.com/@IntelliMate（转化率最好，可以长期转化）
- Facebook page: https://www.facebook.com/profile.php?id=61579913877109#
- X account: https://x.com/IntelliMate2025 (CPM 低、量大）

## 市场推广计划

- [菲律宾市场推广计划书](./PHILIPPINES_MARKETING_PLAN.md) - 3个月验证计划，目标$10,000营收

## Firebase 数据点位信息

### 文档索引

- **[业务事件文档](./FIREBASE_BUSINESS_EVENTS.md)** - 所有业务相关事件的详细说明
- **[事件完整文档](./FIREBASE_EVENTS_DOCUMENTATION.md)** - Analytics 和 Performance 事件的完整列表

### 核心事件说明

1. **message_send_success** - 发送消息并且服务器正确返回的事件（不区分是否触发次数限制，vip限制等）
2. **chat_started** - 第一次发送消息时触发（替换了原来的 chat_session_start）
3. **free_limit_reached** - 免费用户发送消息后，触发了接口返回次数限制的时候上报
4. **chat_session_end** - 退出聊天界面（时机可能不够精准）
5. **message_sent** - 点击发送后，真正触发接口发送时的打点
6. **message_send_failure** - 消息发送接口返回失败
7. **explore_page_view** - Explore 页面的开始展示
8. **app_start** - 启动 App 时触发
