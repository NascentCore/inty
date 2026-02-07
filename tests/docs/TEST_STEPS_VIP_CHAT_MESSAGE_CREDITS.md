<!-- CREATED_BY_AGENT -->
## 目标

验证 VIP 角色聊天扣积分规则与订阅免扣逻辑的单元测试覆盖。

## 测试命令

在仓库根目录执行：

```bash
cd android_app
./gradlew :app:testDebugUnitTest --tests "com.ai.intellimate.chat.utils.VipChatCreditPolicyTest"
```

## 覆盖点

- VIP 标签识别大小写与空值容忍
- 订阅用户免扣
- 非订阅 VIP 扣费判定
