### Android 应用架构级 TODO（android_app 根）

#### P0（必须本期完成）

- [ ] 网络层合并与 SDK 统一
  - [ ] 整合 Retrofit/Moshi 与 Inty SDK 为单一网络层
  - [ ] 统一 OkHttpClient 单例与拦截器（鉴权/日志/重试/缓存）
- [ ] OpenAPI 生成 Kotlin SDK 接入
  - [ ] 接入 OpenAPI 生成 SDK 并替换手写接口
  - [ ] 与后端版本化与错误模型保持一致
- [ ] 依赖注入与配置
  - [ ] 全量采用 Hilt；集中式配置与特性开关
- [ ] UI/状态基线
  - [ ] 统一 Compose（若混用 XML → 迁移计划）
  - [ ] 选择并规范 MVVM/MVI 模式

#### P1（高优先）

- [ ] 数据层与存储
  - [ ] Repository + DataSource 抽象；引入 Room/Proto DataStore 并迁移
- [ ] 离线优先
  - [ ] 请求去重/节流；失败队列与断网重放
- [ ] 可观测性与稳定性
  - [ ] Crash/ANR 收集；启用 StrictMode；网络/业务埋点（含 `x-request-id`）
- [ ] 性能治理
  - [ ] 列表虚拟化；图片加载（Coil）优化；内存与启动时长治理

#### P2（中优先）

- [ ] 无障碍与国际化
  - [ ] 可访问性检查与关键流程文案本地化
- [ ] 质量保障
  - [ ] 契约测试/集成测试；本地 Fake Server 与录制回放
- [ ] 发布与配置
  - [ ] dev/staging/prod 多环境；BuildConfig 与密钥管理
- [ ] 方向限制
  - [ ] 确认仅竖屏支持覆盖全部 Activity 的配置
