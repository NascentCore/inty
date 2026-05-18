# OpenClaw Windows Deployment Scripts

This folder provides an end-to-end deployment flow for OpenClaw on Windows using WSL2.

## Files

- `setup_openclaw_windows.ps1`: Windows entry script (WSL distro setup, systemd enablement, optional onboarding, optional portproxy)
- `setup_openclaw_wsl.sh`: script executed inside WSL for OpenClaw installation

## Recommended path

OpenClaw officially recommends running on Windows via WSL2.

Run in **PowerShell (Administrator recommended)**:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\scripts\openclaw_windows\setup_openclaw_windows.ps1 -Yes
```

If this is your first WSL install and Windows asks for reboot, reboot and rerun the same command.

## Non-interactive onboarding example

If you want the script to finish onboarding automatically, pass an Anthropic API key:

```powershell
.\tools\scripts\openclaw_windows\setup_openclaw_windows.ps1 `
  -AnthropicApiKey "sk-ant-xxx" `
  -Yes
```

## Skip onboarding for later

```powershell
.\tools\scripts\openclaw_windows\setup_openclaw_windows.ps1 -SkipOnboarding -Yes
```

Then in WSL:

```bash
openclaw onboard --install-daemon
```

## Enable LAN access via Windows portproxy

```powershell
.\tools\scripts\openclaw_windows\setup_openclaw_windows.ps1 `
  -EnablePortProxy `
  -PortProxyListenAddress "0.0.0.0" `
  -PortProxyListenPort 18789 `
  -PortProxyTargetPort 18789 `
  -Yes
```

> Note: WSL IP changes after restart, so rerun the script (or refresh portproxy rules) after WSL restarts.

## Dry-run

```powershell
.\tools\scripts\openclaw_windows\setup_openclaw_windows.ps1 -DryRun -Yes
```

This prints planned actions without executing system changes.
