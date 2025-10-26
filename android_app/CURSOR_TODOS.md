### Android 应用架构级 TODO（android_app 根）

- [ ] 架构与分层：单 Activity + Navigation；按功能模块化
- [ ] 依赖注入与配置：统一使用 Hilt；集中式配置与特性开关
- [ ] 网络层合并：整合 Retrofit/Moshi 与 Inty SDK 为单一网络层
- [ ] OkHttpClient 单例与统一拦截器：鉴权/日志/重试/缓存 策略一致
- [ ] 数据层：Repository + DataSource 抽象；Room/Proto DataStore 引入与迁移
- [ ] 离线优先：请求去重/节流；失败队列与断网重放
- [ ] OpenAPI 生成 Kotlin SDK 接入并替换手写接口
- [ ] UI/状态：统一 Compose（若混用 XML → 迁移）；选择并规范 MVVM/MVI
- [ ] 性能：列表虚拟化、图片加载（Coil）优化、内存与启动时长治理
- [ ] 无障碍与国际化：可访问性检查与文案本地化
- [ ] 可观测性：Crash/ANR 收集；StrictMode；网络与业务埋点（携带 x-request-id）
- [ ] 质量保障：契约测试/集成测试；本地 Fake Server 与录制回放
- [ ] 发布与配置：多环境 dev/staging/prod；BuildConfig 与密钥管理
- [ ] 方向限制：确认仅竖屏支持覆盖全部 Activity 的配置
