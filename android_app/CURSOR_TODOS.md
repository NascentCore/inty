### Android应用架构级 TODO（android_app 根）

#### P0（必须本期完成）

- [ ] 网络层合并与 SDK 统一
  - [ ] 整合 Retrofit/Moshi 与 Inty SDK 为单一网络层
  - [ ]统一OkHttpClient单例与拦截器（鉴权/日志/重试/缓​​​​​​​​存）
- [ ] OpenAPI 生成 Kotlin SDK 接入
  - [ ] 接入OpenAPI 生成SDK 替换并手写接口
  - [ ] 与承包商版本化与错误模型保持一致
- [ ] 依赖注入与配置
  - [ ] 全量采用 Hilt；集中式配置与特性开关
- [ ] UI/状态基线
  - [ ]统一Compose（若混用XML → 迁移计划）
  - [ ] 选择并规范MVVM/MVI模式

#### P1（高优先）

- [ ] 数据层与存储
  - [ ] Repository + DataSource抽象；引入Room/Proto DataStore并迁移- [ ] 离线优先- [ ] 请求去重/节流；失败队列与断网重放- [ ] 可安装性与稳定性- [ ] Crash/ANR收集；启用StrictMode；网络/业务埋点（含）`x-request-id`）
- [ ] 治理
  - [ ] 列表虚拟化；图片加载（Coil）优化；内存与启动时长治理

#### P2（中优先）

- [ ]方便与国际化
  - [ ] 可访问性检查与关键流程文案本地化
- [ ] 质量保证
  - [ ] 契约测试/集成测试；本地假服务器与录制回放
- [ ] 发布与配置
  - [ ] dev/staging/prod 多环境；BuildConfig 与密钥管理
- [ ] 方向限制
  - [ ] 确认仅竖屏支持覆盖所有活动的配置