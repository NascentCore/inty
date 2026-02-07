# Android 应用内 "Unable to parse TLS Header" 说明

<!-- CREATED_BY_AGENT -->

## 错误是否以 Toast 显示？

**是的。** 应用在多种网络失败路径下会把**原始错误信息**（包括底层 TLS 异常文案）直接通过 `NetworkErrorHandler` 或 `ToastUtils` 展示给用户，因此 "Unable to parse TLS Header"（或类似 "Unable to parse TLS packet header"）会以 **Toast** 形式出现。

## 在 Android 应用里何时会出现？

该文案来自 **Android/Conscrypt 的 SSL 层**（OkHttp 使用的 TLS 实现），当引擎在期望 TLS 数据时收到了非 TLS 字节（例如 HTTP 明文、代理注入、损坏数据）时抛出。在应用内可能出现的场景包括：

1. **协议不一致**  
   使用 `https://` / `wss://` 连接，但服务端或中间代理实际返回了 HTTP（例如错误页、重定向到 HTTP、端口误配等），首包被当作 TLS 解析 → 解析失败。

2. **代理 / VPN**  
   设备使用 SOCKS5/HTTP 代理或部分 VPN 时，中间节点可能注入、改写或错误转发数据，导致 TLS 引擎收到非 TLS 首包（已知有与部分 VPN 的兼容问题）。

3. **语音通话 WebSocket (wss://)**  
   建立 `wss://` 连接时若服务端或中间层返回非 TLS 数据，会在 `AICallDataSource.connect` → Ktor/OkHttp 的 TLS 握手阶段抛出，异常在 `VoiceCallViewModel` 的 `repository.call(agentId).catch { ... }` 里被捕获并只打日志、不直接弹 Toast；但若同一流程里 **HTTP 请求**（如 `getAgentInfo`）失败并带上该消息，则会通过 `NetworkErrorHandler.showNetworkAwareError(result.message)` 以 Toast 显示。

4. **聊天 / 登录等 HTTPS 请求**  
   任意使用统一 `OkHttpClient` 的请求（聊天发送、拉取消息、登录、设置等）在 TLS 握手或读取阶段失败时，异常信息会经 `HttpResult.Failure(result.message)` 或 `handleNetworkException(e)` 传到 `NetworkErrorHandler`，进而 `ToastUtils.showShort(errorMessage)`，因此用户会看到该 TLS 错误文案。

5. **环境 / URL 配置**  
   本地环境使用 `baseUrl = "http://..."` 且 `websocketAddress = "wss://..."`；若本地 WS 服务未正确提供 TLS，`wss://` 连接也可能触发同类错误。Release/Play 使用 `https` + `wss`，若 CDN/网关返回非 TLS 响应（如错误页）也会触发。

## 代码路径（Toast 来源）

| 场景 | 调用链 | Toast 内容来源 |
|------|--------|----------------|
| 聊天发送/继续对话失败 | `ChatViewModel` → `NetworkErrorHandler.showNetworkAwareError(result.message)` 或 `handleNetworkException(e)` | `result.message` / `e.message` |
| 设置 Agent 失败 | `ChatViewModel.setAgentID` catch → `NetworkErrorHandler.handleNetworkException(e)` | `e.message` |
| 登录失败（后端返回错误） | `MainActivity` HttpResult.Failure → `showNetworkAwareError(loginResult.message)` | `loginResult.message` |
| 语音通话前拉取角色信息失败 | `AICallRepository.getAgentInfo` → HttpResult.Failure → `showNetworkAwareError(result.message)` | `result.message` |
| 语音通话内服务端下发的错误 | `VoiceCallScreen` 根据 `IntyErrorCode` 显示 Dialog 或 `ToastUtils.showShort(it.second)` | 服务端 `error_code` 对应文案（通常不是 TLS 底层异常） |
| WebSocket 连接失败（未再包装成业务错误时） | `VoiceCallViewModel.call().catch { ... }` 仅打日志、更新 `connectionState`，**不**把 `error.message` 送 Toast | 若用户仍看到 TLS Toast，多半来自同流程中的 **HTTP 请求**（如 `getAgentInfo`）失败 |
| 设置/账号/删除等 HTTP 异常 | `SettingViewModel` / `ProfileViewModel` 等 → `HttpErrorHandler.handleGeneralException(e)` → 返回 `e.message` 或包装文案 → `ToastUtils.showShort(errorMessage)` | 若异常未命中 timeout/network/json 分支，会返回原始 `e.message`（含 TLS 时即会展示） |
| 头像/自拍选择时异常 | `UploadSelfieScreen`、`ImagePickerBottomSheet`、`ChatMessageItems` 中 catch → `ToastUtils.showShort(error.localizedMessage.orEmpty())` | 拍照/选图流程中若触发网络或 IO 异常（如请求 CDN/上传），原始异常文案会直接 Toast |
| 角色详情/刷新角色 | `AgentInfoViewModel.getAgentInfo` / `refreshAgentData` → `showNetworkAwareError(result.message)` | 同 A |
| VIP 购买前置失败 | `VipCenterViewModel` → `showNetworkAwareError(error)` | 同 A |

结论：**TLS 解析错误以 Toast 出现，是因为某次 HTTP 或 WebSocket 底层失败后，异常/失败消息被原样传入 `NetworkErrorHandler`、`HttpErrorHandler` 的返回值，或直接 `ToastUtils.showShort(exception.message/localizedMessage)`，未做友好文案转换。**

## 用户端无法复现时如何收集（Firebase Crashlytics）

开发环境无法复现时，可在**用户设备发生** TLS/parse 错误时自动上报到 **Firebase Crashlytics**（非致命异常），便于在控制台看到设备、系统版本、发生路径等。

- **实现方式**：在检测到错误文案含 "TLS" 或 "parse" 的路径中，除写本地 debug.log 外，会调用 `FirebaseManager.recordException(...)`，并附带自定义键：
  - `tls_parse_hypothesis_id`：假设 ID（A–H），对应下表路径
  - `tls_parse_location`：代码位置
  - `tls_parse_message`：错误文案截断（前 200 字符，不包含敏感信息）
- **无需用户操作**：上报在现有错误处理路径中自动执行，用户无感知。

**在 Firebase 控制台如何查看：**

1. 打开 [Firebase Console](https://console.firebase.google.com/) → 选择项目 → 左侧菜单 **Crashlytics**。
2. 顶部切换到 **「非致命异常」**（Non-fatal issues）。若界面是英文，为 "Non-fatal issues" 或 "Issues" 下筛选 non-fatal。
3. 在问题列表上方的**搜索框**输入 **`TLS_PARSE_ERROR`**，或向下滚动找到异常信息以 `TLS_PARSE_ERROR [hypothesisId=...]` 开头的那一类。
4. 点击该问题进入详情页，可看到：
   - **设备/系统/应用版本**：每台发生过的设备一行，系统版本、应用版本等；
   - **自定义键**（在单次事件详情里）：`tls_parse_hypothesis_id`、`tls_parse_location`、`tls_parse_message`，用于判断是 A–H 哪条路径及错误文案。
5. 若未单独列出，可在 Crashlytics 的 **「全部」/「Issues」** 里搜索 `TLS_PARSE`，再点进对应 issue 查看非致命上报及上述 keys。
6. **自定义键**通常在「事件详情」里：点进某次发生记录（按设备/时间列出的某一条），在详情面板中查看 Keys 或 Logs，即可看到 `tls_parse_hypothesis_id` 等。

## 调试埋点与假设 ID（hypothesisId）

复现时若 `.cursor/debug.log` 或 logcat 中出现下列 ID，可对应到具体路径；同一 ID 也会出现在 Crashlytics 的 `tls_parse_hypothesis_id` 中：

| hypothesisId | 含义 | 位置 |
|--------------|------|------|
| A | 通过 `NetworkErrorHandler.showNetworkAwareError` 展示（聊天/登录/getAgentInfo/VIP 等 HTTP 失败） | NetworkErrorHandler.kt |
| B | 通过 `NetworkErrorHandler.handleNetworkException` 展示（如 setAgentID 等异常） | NetworkErrorHandler.kt |
| C | WebSocket 连接阶段在 `VoiceCallViewModel.call().catch` 中抛出（此处不弹 Toast，仅打日志） | VoiceCallViewModel.kt |
| D | 语音通话界面用服务端下发的错误文案弹 Toast | VoiceCallScreen.kt |
| E | 通过 `HttpErrorHandler.handleGeneralException` 返回含 TLS/parse 的文案，由 Setting/Profile 等调用方 Toast | HttpErrorHandler.kt |
| F | 自拍/上传流程中 `UploadSelfieScreen` 将 `error.localizedMessage` 直接 Toast | UploadSelfieScreen.kt |
| G | 图片选择底部栏中 `ImagePickerBottomSheet` 将 `error.localizedMessage` 直接 Toast | ImagePickerBottomSheet.kt |
| H | 聊天消息项中 `ChatMessageItems` 将 `error.localizedMessage` 直接 Toast（如选图/拍照） | ChatMessageItems.kt |

## 参考资料

- [Stack Overflow: Unable to parse TLS packet header](https://stackoverflow.com/questions/67360263/unable-to-parse-tls-packet-header-android-studio)  
- [ConscryptEngine: Unable to parse TLS packet header](https://stackoverflow.com/questions/63337561/conscryptengine-data-read-issue-unable-to-parse-tls-packet-header)  
- OkHttp/Conscrypt：在 TLS 握手时若收到非 TLS 数据会抛出包含 "Unable to parse TLS..." 的异常。

---

## 改动总结与后续流程

### 一、所有改动汇总

| 类型 | 文件 | 改动说明 |
|------|------|----------|
| **文档** | `docs/ANDROID_TLS_PARSE_ERROR.md` | 新增：错误成因、Toast 代码路径、假设 ID 表、Crashlytics 收集说明、本总结与后续流程。 |
| **埋点 + 上报** | `app/.../utils/NetworkErrorHandler.kt` | 新增 `reportTlsParseToFirebase`、`writeTlsParseDebugLog`、`writeTlsParseDebugLogIfRelevant`：当错误文案含 "TLS" 或 "parse" 时写本地 `debug.log` 并上报 Crashlytics（非致命），带 hypothesisId A/B。在 `showNetworkAwareError` / `handleNetworkException` 入口处调用上述埋点。 |
| **埋点 + 上报** | `app/.../utils/HttpErrorHandler.kt` | 在 `handleGeneralException` 的 else 分支中调用 `NetworkErrorHandler.writeTlsParseDebugLogIfRelevant("E", ...)`，对含 TLS/parse 的异常做写 log + Crashlytics。 |
| **埋点 + 上报** | `app/.../call/VoiceCallViewModel.kt` | 在 `call(agentId).catch` 中调用 `writeTlsParseDebugLogIfRelevant("C", ...)`，覆盖 WebSocket 连接失败路径。 |
| **埋点 + 上报** | `app/.../call/VoiceCallScreen.kt` | 在语音错误 Toast 的 else 分支中调用 `writeTlsParseDebugLogIfRelevant("D", ...)`。 |
| **埋点 + 上报** | `app/.../profile/UploadSelfieScreen.kt` | 在 catch 中调用 `writeTlsParseDebugLogIfRelevant("F", ...)`。 |
| **埋点 + 上报** | `app/.../ui/components/ImagePickerBottomSheet.kt` | 在 catch 中调用 `writeTlsParseDebugLogIfRelevant("G", ...)`。 |
| **埋点 + 上报** | `app/.../chat/ui/ChatMessageItems.kt` | 在 catch 中调用 `writeTlsParseDebugLogIfRelevant("H", ...)`。 |

逻辑约定：**仅当**错误文案中包含 "TLS" 或 "parse"（不区分大小写）时才写 log 并上报，避免无关错误刷屏。

---

### 二、后续如何收集数据

- **本地/自测能复现时**
  - 看本机 ` .cursor/debug.log`（NDJSON，一行一条），根据 `hypothesisId`、`location`、`data.errorMessage` 定位是 A–H 中哪条路径。
  - 或看 logcat 中 "连接语音通话失败" 等已有日志，配合路径判断。

- **用户端无法复现时（主要场景）**
  - 发版后依赖 **Firebase Crashlytics** 自动收集：
    1. 打开 Firebase Console → 项目 → **Crashlytics**。
    2. 切到 **非致命异常**（Non-fatal issues）。
    3. 搜索或筛选异常信息包含 **`TLS_PARSE_ERROR`** 的条目。
    4. 点进单条，查看：
       - **自定义键**：`tls_parse_hypothesis_id`（A–H）、`tls_parse_location`、`tls_parse_message`（截断）。
       - **设备/系统/应用版本**：Crashlytics 自带。
  - 据此统计：哪类路径最多（聊天/登录/语音/设置/选图）、哪些机型/系统版本高发，用于优先修复和复现尝试。

---

### 三、如何用收集到的数据解决问题

1. **根据 hypothesisId 确定场景**
   - **A**：聊天发送、登录、getAgentInfo、VIP 等 **HTTP 请求** 失败 → 查服务端/网关/CDN 是否对该请求返回了非 TLS 或错误页；查用户网络/代理/VPN。
   - **B**：设置 Agent 等流程里 **handleNetworkException** → 同上，重点看请求 URL 与当时网络环境。
   - **C**：**语音 WebSocket 连接** 阶段失败（未弹 Toast，但已上报）→ 查 wss 服务端或中间层是否对连接返回了非 TLS 数据；可与 A 结合看是否同一次进语音时 getAgentInfo 也失败（A 会弹 Toast）。
   - **D**：语音通话中 **服务端下发的错误文案** 含 TLS/parse → 多为服务端把底层异常直接下发给客户端，需后端对错误做脱敏或友好文案。
   - **E**：设置/账号/删除等 **HttpErrorHandler.handleGeneralException** 返回了原始 `e.message` → 可在该 handler 里对含 "TLS"/"parse" 的 message 做映射为通用提示，避免把底层异常直接给用户看。
   - **F/G/H**：自拍或选图流程里 **本地异常**（如 IO/权限）文案含 parse 等 → 较少见；若确认是网络相关，再按 A/B 思路查。

2. **常见根因与对应措施**
   - **协议/环境不一致**：确认 baseUrl/websocketAddress 的 scheme 与真实服务一致（https/wss 对应端到端 TLS）；检查 CDN/网关是否对错误响应返回了 HTTP 或 HTML 错误页。
   - **代理/VPN**：部分 VPN 或企业代理会改写 TLS 流 → 在文档或 FAQ 中说明，或对已知不可用网络给出友好提示。
   - **用户体验**：无论根因是否短期可修，都建议对 **含 "TLS" 或 "parse" 的异常** 在展示前做统一映射（如 "Network error, please try again"），避免原始 Conscrypt/OkHttp 文案直接 Toast；Crashlytics 仍保留完整信息用于排查。

3. **修复后的验证**
   - 若做了文案映射或环境修复：继续保留当前埋点与 Crashlytics 上报一段时间，通过 Crashlytics 中 `TLS_PARSE_ERROR` 是否减少、以及是否仍有相同 hypothesisId 的反馈，验证是否生效。
   - 确认无新反馈后，再视需要移除或收缩埋点（例如仅保留 Crashlytics 上报、关闭写 debug.log）。
