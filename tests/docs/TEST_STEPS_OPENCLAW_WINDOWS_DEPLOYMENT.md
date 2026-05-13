# TEST_STEPS_OPENCLAW_WINDOWS_DEPLOYMENT

## 目标

验证 `tools/scripts/openclaw_windows/setup_openclaw_windows.ps1` 能在 Windows + WSL2 场景下完成 OpenClaw 部署与基础验收。

## 前置条件

- Windows 11（建议）或已支持 WSL2 的 Windows 10
- 可访问互联网（下载 WSL/Node/OpenClaw）
- PowerShell 可用

## 用例 1：Dry-run

在 Windows PowerShell 中执行：

```powershell
.\tools\scripts\openclaw_windows\setup_openclaw_windows.ps1 -DryRun -Yes
```

预期：

- 输出包含 WSL 安装、systemd 设置、WSL 内安装脚本执行、可选 onboarding/验证动作的 dry-run 信息
- 不会执行实际系统改动

## 用例 2：标准安装（交互式 onboarding）

在 Windows PowerShell 中执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\scripts\openclaw_windows\setup_openclaw_windows.ps1 -Yes
```

若提示首次安装 WSL 需重启，重启后重复执行同一命令。

预期：

- 若 `systemd=true` 尚未配置，脚本会写入 `/etc/wsl.conf`、执行 `wsl --shutdown`，提示重新执行
- 再次执行后会进入 WSL 安装 OpenClaw
- 启动 `openclaw onboard --install-daemon` 交互流程

## 用例 3：非交互 onboarding

在 Windows PowerShell 中执行：

```powershell
.\tools\scripts\openclaw_windows\setup_openclaw_windows.ps1 `
  -AnthropicApiKey "sk-ant-xxx" `
  -Yes
```

预期：

- 脚本执行非交互 onboarding
- 完成后自动执行：
  - `openclaw doctor --non-interactive`
  - `openclaw gateway status`
  - `openclaw status --all`

## 用例 4：启用 portproxy（LAN 暴露）

在管理员 PowerShell 中执行：

```powershell
.\tools\scripts\openclaw_windows\setup_openclaw_windows.ps1 `
  -EnablePortProxy `
  -PortProxyListenAddress "0.0.0.0" `
  -PortProxyListenPort 18789 `
  -PortProxyTargetPort 18789 `
  -Yes
```

预期：

- 创建/刷新 `netsh interface portproxy` 规则
- 新增（或重建）Windows 防火墙入站规则 `OpenClaw WSL Gateway 18789`
- 输出当前映射的 WSL IP 与端口

## 回归验证

在 WSL 内执行：

```bash
openclaw doctor --non-interactive
openclaw gateway status
openclaw status --all
openclaw dashboard
```

预期：

- `doctor` 无阻断错误
- `gateway status` 显示运行中
- `status --all` 可返回完整状态
- `dashboard` 可打开控制台 URL
