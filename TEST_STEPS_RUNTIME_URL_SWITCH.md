# 运行时后端 URL 切换功能 - 完整测试步骤

## 测试环境准备

### 前置条件
1. 确保使用 **debug** build type 编译应用
2. 准备至少 2 个可用的后端服务器（例如：dev、prod、local）
3. 确保设备/模拟器可以访问这些后端服务器

### 测试数据准备
- **Dev 环境**: `https://dev.inty.sxwl.ai/` (或实际 dev 地址)
- **Prod 环境**: `https://app.inty.cc/` (或实际 prod 地址)
- **Local 环境**: `http://10.0.2.2:8000/` (或实际 local 地址)
- 测试账号：准备一个有效的登录账号用于测试

---

## 测试用例 1: 基础功能测试

### 1.1 UI 可见性测试
**目标**: 验证 UI 仅在 debug build 下显示

**步骤**:
1. 使用 **debug** build type 编译并安装应用
2. 打开应用，进入 **Settings** 页面
3. 向下滚动，查找 **Debug Backend Endpoint** 卡片

**预期结果**:
- ✅ **Debug Backend Endpoint** 卡片可见
- ✅ 显示当前构建类型：`debug`
- ✅ 显示当前后端地址（默认应为 dev 地址）
- ✅ 显示三个预设按钮：`local`、`dev`、`prod`
- ✅ 显示"恢复默认"按钮

**验证点**:
- [ ] UI 元素完整显示
- [ ] 当前 URL 显示正确（应与默认 dev 地址一致）

---

### 1.2 预设 URL 切换测试
**目标**: 验证通过预设按钮切换 URL 功能

**步骤**:
1. 在 Settings 页面找到 **Debug Backend Endpoint** 卡片
2. 记录当前显示的后端地址（假设为 dev）
3. 点击 **`prod`** 预设按钮
4. 观察 UI 更新
5. 执行一个网络请求（例如：刷新 Explore 页面）
6. 检查网络请求是否发送到 prod 地址

**预期结果**:
- ✅ UI 中的"当前后端地址"立即更新为 prod 地址
- ✅ 网络请求发送到 prod 服务器
- ✅ 请求成功（如果 prod 服务器可用）

**验证点**:
- [ ] UI 状态立即更新
- [ ] 网络请求 URL 正确（可通过网络抓包工具验证，如 Charles、Fiddler）
- [ ] 请求成功返回数据

**回退测试**:
1. 点击 **`dev`** 预设按钮
2. 验证 URL 切换回 dev
3. 执行网络请求，验证请求发送到 dev 服务器

---

### 1.3 恢复默认配置测试
**目标**: 验证"恢复默认"功能

**步骤**:
1. 切换到非默认 URL（例如：切换到 `prod`）
2. 点击 **"恢复默认"** 按钮
3. 观察 UI 更新
4. 执行网络请求

**预期结果**:
- ✅ UI 中的"当前后端地址"恢复为默认 dev 地址
- ✅ 网络请求发送到默认 dev 服务器

**验证点**:
- [ ] URL 恢复为默认值
- [ ] 网络请求使用默认 URL

---

## 测试用例 2: 缓存机制测试

### 2.1 Inty SDK 缓存测试
**目标**: 验证 Inty SDK 客户端缓存机制

**步骤**:
1. 确保当前 URL 为 dev
2. 执行一个使用 Inty SDK 的请求（例如：获取用户信息）
3. 在 Settings 中切换到 prod URL
4. 立即执行相同的 Inty SDK 请求
5. 检查请求是否发送到 prod 服务器

**预期结果**:
- ✅ 第一次请求发送到 dev 服务器
- ✅ 切换 URL 后，第二次请求发送到 prod 服务器
- ✅ 没有使用旧的 dev 客户端

**验证方法**:
- 使用网络抓包工具（Charles/Fiddler）监控请求
- 检查请求的 Host header 或完整 URL

**验证点**:
- [ ] 切换 URL 后，新请求使用新 URL
- [ ] 旧客户端缓存被清除

---

### 2.2 Retrofit 缓存测试
**目标**: 验证 Retrofit 客户端缓存机制

**步骤**:
1. 确保当前 URL 为 dev
2. 执行一个使用 Retrofit 的请求（例如：Explore 页面的推荐 agents）
3. 在 Settings 中切换到 prod URL
4. 立即执行相同的 Retrofit 请求
5. 检查请求是否发送到 prod 服务器

**预期结果**:
- ✅ 第一次请求发送到 dev 服务器
- ✅ 切换 URL 后，第二次请求发送到 prod 服务器
- ✅ 没有使用旧的 dev Retrofit 实例

**验证方法**:
- 使用网络抓包工具监控请求
- 检查请求的完整 URL

**验证点**:
- [ ] 切换 URL 后，新请求使用新 URL
- [ ] 旧 Retrofit 实例缓存被清除

---

### 2.3 混合缓存测试
**目标**: 验证同时使用 Inty SDK 和 Retrofit 的场景

**步骤**:
1. 确保当前 URL 为 dev
2. 执行一个 Inty SDK 请求（例如：用户信息）
3. 执行一个 Retrofit 请求（例如：推荐 agents）
4. 在 Settings 中切换到 prod URL
5. 再次执行上述两个请求

**预期结果**:
- ✅ 所有请求都切换到 prod 服务器
- ✅ 没有请求发送到旧的 dev 服务器

**验证点**:
- [ ] Inty SDK 请求使用新 URL
- [ ] Retrofit 请求使用新 URL
- [ ] 所有请求都正确切换

---

## 测试用例 3: 持久化测试

### 3.1 应用重启持久化测试
**目标**: 验证 URL 覆盖在应用重启后仍然有效

**步骤**:
1. 在 Settings 中切换到 prod URL
2. 完全关闭应用（从最近任务中清除）
3. 重新启动应用
4. 进入 Settings 页面，查看 **Debug Backend Endpoint** 卡片
5. 执行一个网络请求

**预期结果**:
- ✅ UI 中显示的 URL 仍然是 prod（不是默认 dev）
- ✅ 网络请求发送到 prod 服务器

**验证点**:
- [ ] URL 覆盖在重启后保持
- [ ] 网络请求使用覆盖的 URL

---

### 3.2 清除覆盖后重启测试
**目标**: 验证清除覆盖后，重启应用恢复默认

**步骤**:
1. 切换到 prod URL
2. 点击"恢复默认"
3. 完全关闭应用
4. 重新启动应用
5. 进入 Settings 页面查看 URL
6. 执行网络请求

**预期结果**:
- ✅ UI 中显示的 URL 是默认 dev
- ✅ 网络请求发送到默认 dev 服务器

**验证点**:
- [ ] 清除覆盖后，重启应用恢复默认 URL

---

## 测试用例 4: 边界情况测试

### 4.1 快速连续切换测试
**目标**: 验证快速连续切换 URL 不会导致问题

**步骤**:
1. 快速连续点击不同的预设按钮（例如：dev → prod → local → dev）
2. 每次切换后执行一个网络请求
3. 检查是否有错误或崩溃

**预期结果**:
- ✅ 应用不会崩溃
- ✅ 每次请求都使用正确的 URL
- ✅ 没有内存泄漏或性能问题

**验证点**:
- [ ] 无崩溃
- [ ] 无异常日志
- [ ] 请求 URL 正确

---

### 4.2 切换 URL 后立即请求测试
**目标**: 验证切换 URL 后立即请求不会使用旧缓存

**步骤**:
1. 确保当前 URL 为 dev
2. 执行一个请求（确保请求正在进行）
3. 在请求完成前，立即切换到 prod URL
4. 立即执行另一个请求
5. 检查两个请求的 URL

**预期结果**:
- ✅ 第一个请求可能发送到 dev（如果已经开始）
- ✅ 第二个请求必须发送到 prod
- ✅ 没有竞态条件问题

**验证点**:
- [ ] 新请求使用新 URL
- [ ] 无竞态条件

---

### 4.3 不同 Token 场景测试
**目标**: 验证切换 URL 时，不同 token 的客户端缓存正确处理

**步骤**:
1. 使用账号 A 登录，URL 为 dev
2. 执行一些请求
3. 切换到 prod URL
4. 执行请求
5. 登出账号 A
6. 使用账号 B 登录，URL 仍为 prod
7. 执行请求

**预期结果**:
- ✅ 账号 A 的 dev 客户端被正确清理
- ✅ 账号 A 的 prod 客户端被正确创建
- ✅ 账号 B 的 prod 客户端被正确创建
- ✅ 没有使用错误的 token 或 URL

**验证点**:
- [ ] 不同账号的客户端隔离正确
- [ ] 不同 URL 的客户端隔离正确

---

## 测试用例 5: 功能完整性测试

### 5.1 所有 API 类型测试
**目标**: 验证所有类型的 API 请求都支持 URL 切换

**测试场景**:
1. **Inty SDK APIs**:
   - [ ] 用户信息 API (`UserService`)
   - [ ] 认证 API (`AuthService`)
   - [ ] 智能体 API (`AgentService`)
   - [ ] 聊天 API (`ChatService`)
   - [ ] 订阅 API (`SubscriptionService`)

2. **Retrofit APIs**:
   - [ ] 用户 API (`IUserApi`)
   - [ ] 智能体 API (`IAgentApi`)
   - [ ] 聊天 API (`IChatApi`)
   - [ ] 订阅 API (`ISubscriptionApi`)
   - [ ] 通用 API (`ICommonApi`)

**步骤**:
1. 切换到 dev URL
2. 执行每种类型的 API 请求
3. 切换到 prod URL
4. 再次执行每种类型的 API 请求
5. 验证所有请求都使用正确的 URL

**预期结果**:
- ✅ 所有类型的 API 请求都正确切换 URL
- ✅ 没有遗漏的 API 类型

---

### 5.2 页面功能测试
**目标**: 验证各个页面的功能在 URL 切换后正常工作

**测试页面**:
- [ ] **Explore 页面**: 推荐智能体列表
- [ ] **Chat 页面**: 聊天功能
- [ ] **Profile 页面**: 用户信息
- [ ] **Settings 页面**: 设置功能
- [ ] **Agent Info 页面**: 智能体详情

**步骤**:
1. 切换到 dev URL
2. 测试每个页面的主要功能
3. 切换到 prod URL
4. 再次测试每个页面的主要功能

**预期结果**:
- ✅ 所有页面功能正常
- ✅ 所有网络请求使用正确的 URL

---

## 测试用例 6: 安全性测试

### 6.1 Build Type 限制测试
**目标**: 验证功能仅在 debug build 下可用

**步骤**:
1. 使用 **release** build type 编译应用
2. 安装并打开应用
3. 进入 Settings 页面
4. 查找 **Debug Backend Endpoint** 卡片

**预期结果**:
- ✅ **Debug Backend Endpoint** 卡片**不可见**
- ✅ 无法通过任何方式切换 URL

**验证点**:
- [ ] UI 不显示
- [ ] 功能不可用

---

### 6.2 非 Debug App 测试
**目标**: 验证非调试构建的 App 无法使用此功能

**步骤**:
1. 使用 debug build type，但确保 `AppUtils.isAppDebug()` 返回 false（如果可能）
2. 尝试切换 URL

**预期结果**:
- ✅ 功能不可用
- ✅ 有适当的错误提示（如果有）

---

## 测试用例 7: 性能测试

### 7.1 切换性能测试
**目标**: 验证切换 URL 的性能

**步骤**:
1. 记录切换 URL 的时间
2. 执行多次切换，计算平均时间
3. 检查是否有明显的性能问题

**预期结果**:
- ✅ 切换时间 < 100ms（理想情况下）
- ✅ 无明显的 UI 卡顿

---

### 7.2 内存泄漏测试
**目标**: 验证切换 URL 不会导致内存泄漏

**步骤**:
1. 使用 Android Profiler 监控内存
2. 多次切换 URL（例如：50 次）
3. 检查内存使用情况
4. 执行 GC，检查是否有内存泄漏

**预期结果**:
- ✅ 内存使用稳定
- ✅ 无内存泄漏

---

## 测试检查清单

### 功能检查
- [ ] UI 可见性（仅 debug build）
- [ ] 预设 URL 切换
- [ ] 恢复默认配置
- [ ] 应用重启持久化
- [ ] 所有 API 类型支持

### 缓存机制检查
- [ ] Inty SDK 缓存正确
- [ ] Retrofit 缓存正确
- [ ] 混合使用场景正确
- [ ] 不同 token 场景正确

### 边界情况检查
- [ ] 快速连续切换
- [ ] 切换后立即请求
- [ ] 不同账号场景

### 安全性检查
- [ ] Build type 限制
- [ ] 非 debug app 限制

### 性能检查
- [ ] 切换性能
- [ ] 内存泄漏

---

## 测试工具推荐

1. **网络抓包工具**:
   - Charles Proxy
   - Fiddler
   - Android Studio Network Profiler

2. **性能分析工具**:
   - Android Studio Profiler
   - LeakCanary（如果已集成）

3. **日志工具**:
   - Android Studio Logcat
   - 查看 `DebugBackendEndpointStore` 和 `IntyNetworkManager` 的日志

---

## 常见问题排查

### 问题 1: 切换 URL 后请求仍发送到旧 URL
**可能原因**:
- 缓存未清除
- 请求在切换前已开始

**排查步骤**:
1. 检查日志，确认 `clearClientCache()` 和 `clearCache()` 被调用
2. 使用网络抓包工具确认请求 URL
3. 检查是否有其他地方缓存了客户端

### 问题 2: UI 显示不正确
**可能原因**:
- StateFlow 未更新
- UI 未正确观察状态

**排查步骤**:
1. 检查 `DebugBackendSettingsViewModel.uiState` 的值
2. 检查 `NetworkConfig.getBaseUrl()` 的返回值
3. 检查 `DebugBackendEndpointStore.getOverrideInfo()` 的返回值

### 问题 3: 应用重启后 URL 恢复默认
**可能原因**:
- SharedPreferences 未正确保存
- 读取时机不对

**排查步骤**:
1. 检查 SharedPreferences 文件：`debug_network_config`
2. 检查应用启动时 `NetworkConfig.setBuildType()` 的调用时机
3. 检查 `DebugBackendEndpointStore.getOverrideInfo()` 的调用时机

---

## 测试报告模板

```
测试日期: ___________
测试人员: ___________
Build Type: debug
Build Version: ___________

### 测试结果汇总
- 总测试用例数: ___
- 通过: ___
- 失败: ___
- 跳过: ___

### 发现的问题
1. [问题描述]
   - 严重程度: [高/中/低]
   - 复现步骤: 
   - 预期结果: 
   - 实际结果: 

### 建议
1. [建议内容]
```

