# 运行时后端 Endpoint 切换指南

CREATED_BY_AGENT

本指南面向 Android 客户端开发/QA，说明如何在**无需重新编译 APK**的情况下，切换 App 所访问的后端环境（dev/local/prod 或自定义环境）。

## 基本原理

- `core/data/src/main/assets/backend_endpoints.defaults.json` 提供出厂默认映射（包含 prod/dev/local）。
- App 首次启动时会将该文件复制到应用私有目录 `files/config/backend_endpoints.json`，运行时所有网络请求都读取这个副本。
- `BackendEnvironmentManager` 持续监听配置文件；一旦内容或位置变更，`NetworkConfig`、`NetServiceMgr`、`IntyNetworkManager` 会同步刷新 `baseUrl`，新的请求立即走到最新 endpoint。

## 查看/备份当前配置

1. 连接设备（真机需 `adb tcpip` 或 USB 调试）。
2. 通过 `adb shell run-as com.ai.intellimate ls files/config` 确认目录存在。
3. 导出当前配置：
   ```bash
   adb shell run-as com.ai.intellimate cat files/config/backend_endpoints.json > backend_endpoints.backup.json
   ```
4. 建议在修改前留一份备份，方便恢复。

## 修改 target endpoint

### 方法一：Android Studio Device File Explorer

1. 打开 Device File Explorer，路径：`data/data/com.ai.intellimate/files/config/`.
2. 将 `backend_endpoints.json` 复制到本机编辑，或直接右键 `Save As…`。
3. 修改 `environments` 中的 `base_url` 或新增一个 `id`（确保 URL 包含 `http/https` 并以 `/` 结尾）。
4. 保存后重新上传覆盖原文件（同名 drag & drop）。
5. 重启 App 或从最近任务中滑掉再打开，日志中可看到 `BackendEnvironmentManager 已加载运行时配置`。

### 方法二：命令行（适合批量/CI）

```bash
# 推送新的配置文件
adb push backend_endpoints.custom.json /sdcard/Download/backend_endpoints.json

# 拷贝到 App 私有目录
adb shell
run-as com.ai.intellimate sh -c 'cp /sdcard/Download/backend_endpoints.json files/config/backend_endpoints.json && chmod 600 files/config/backend_endpoints.json'
exit
```

> 也可直接使用 `printf '...' | adb shell run-as com.ai.intellimate cat > files/config/backend_endpoints.json` 动态生成内容。

## 切换构建类型映射

- `build_type_overrides` 映射 Gradle 构建类型（`local/debug/playdebug/release`）到 `environments[].id`。
- 例如希望 `debug` 构建访问本地服务：
  ```json
  "build_type_overrides": {
    "debug": "local",
    "playdebug": "dev",
    "release": "prod",
    "local": "local"
  }
  ```
- 若缺失映射，会回退到 `default_env`，再不行则使用 `Constant.USER_HOST*` 内置常量。

## 新增自定义环境

在 `environments` 数组追加条目：

```json
{
  "id": "qa-sh",
  "label": "QA Shanghai",
  "base_url": "https://qa-sh.inty.cc/",
  "aliases": ["qa", "qa-sh"],
  "notes": "与 QA 团队共享的灰度后端"
}
```

- `id`：唯一标识；`base_url` 必须包含协议，末尾保留 `/`。
- `aliases`：可选，用于让 `BackendEnvironmentManager.getBaseUrlFor("qa")` 命中此环境。
- 设置完毕后修改 `build_type_overrides` 或在 App 内部（未来 Dev Settings）使用 `BackendEnvironmentManager.refresh()` 切换。

## 恢复默认配置

```bash
adb shell run-as com.ai.intellimate rm files/config/backend_endpoints.json
adb shell run-as com.ai.intellimate rm -r files/config 2>/dev/null # 可选
adb shell run-as com.ai.intellimate am force-stop com.ai.intellimate
adb shell monkey -p com.ai.intellimate -c android.intent.category.LAUNCHER 1
```

首次启动会重新从 assets 复制默认文件。

## 常见问题

- **修改后仍访问旧后端？** 确认文件写入成功，并重新进入 App；查看 Logcat 搜索 `BackendEnvironmentManager` 是否输出“已加载运行时配置”。
- **JSON 语法错误？** 管理器会自动回退内置配置，并在日志中提示“解析运行时配置失败”；修复文件后重新打开 App。
- **想同时切换 Retrofit 与 Inty SDK？** 已统一使用 `NetworkConfig.getBaseUrl()`，无需额外操作。

如需在 UI 中提供环境选择入口，可直接调用 `BackendEnvironmentManager.getAvailableEnvironments()` 列出选项，并在用户确认后写回 `backend_endpoints.json` 或调用未来的设置接口。若遇到无法恢复的异常，请携带 `backend_endpoints.json` 与 Logcat 输出向客户端基础设施负责人反馈。
