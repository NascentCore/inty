# 动态调整后端 URL 不用重新编译，直接运行时修改（或者只需要可以忽略的时间）

在测试中需要调用本地后端服务，方便测试端到端功能。
但是目前指向后端的配置 URL 是根据 build type 动态设置，每次修改需要重新编译（缓存无效）。
本设计旨在提供实时修改后端 api 地址的方法。

# 方案：

1. 现统一原有的网络库network的使用，和inty sdk的网络库的okhttp的client
2. 对buildType（现有debug、playdebug、release和local）不同配置url
3. 对第一点已经统一后的client配置动态baseUrl，通过缓存文件形式保存，并在app启动配置阶段生效
4. 创建一个非release可以使用的依赖模块和UI功能，用于切换BaseUrl

## 2025-11 实现状态

- `NetworkConfig` 接入 `DebugBackendEndpointStore`，仅在 `debug` build type 且 App 为调试构建时才会读取/写入运行时 Base URL 覆盖值。
- 覆盖信息存储在 `SharedPreferences(debug_network_config)` 中，应用启动阶段（`IntyNetworkManager.initialize` → `NetworkConfig.setBuildType`）即可加载，且会影响数据层和 Inty SDK 的客户端缓存 key。
- 设置页面新增 **Debug Backend Endpoint** 卡片（仅 `debug` 构建可见），支持：
  - 查看当前生效/覆盖的 Base URL 及最后更新时间；
  - 直接输入自定义 URL（自动补齐 scheme 与 `/`）并一键切换；
  - 使用 `Dev / Prod / Local` 预设快捷按钮；
  - 恢复默认配置并自动清空 `IntyNetworkManager` 的 client cache。
- 切换后无需重启或重新编译，新的 Base URL 会在下一次网络请求中立即生效。

### 使用步骤（Debug 构建）

1. 编译安装 `debug` build type。
2. 打开 **Settings → Debug Backend Endpoint** 卡片。
3. 选择预设或输入目标 URL，点击「立即切换」。
4. 若需回到默认值，点击「恢复默认」即可。
