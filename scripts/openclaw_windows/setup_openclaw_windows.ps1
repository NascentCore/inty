[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu-24.04",
    [ValidateSet("installer", "npm", "pnpm", "source")]
    [string]$InstallMode = "installer",
    [int]$GatewayPort = 18789,
    [string]$OpenClawVersion = "latest",
    [switch]$SkipOnboarding,
    [string]$AnthropicApiKey = "",
    [switch]$EnablePortProxy,
    [string]$PortProxyListenAddress = "0.0.0.0",
    [int]$PortProxyListenPort = 18789,
    [int]$PortProxyTargetPort = 18789,
    [switch]$DryRun,
    [switch]$Yes
)

# 核心流程：准备 WSL 与 systemd -> 调用 WSL 安装脚本 -> 执行 onboarding -> 验收 -> 可选端口映射。
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[openclaw-win] $Message"
}

function Invoke-External {
    param(
        [string]$Description,
        [scriptblock]$Action
    )
    if ($DryRun) {
        Write-Host "[dry-run] $Description"
        return
    }
    Write-Step $Description
    & $Action
}

function Get-WslDistros {
    $items = & wsl --list --quiet 2>$null
    return @($items | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })
}

function Invoke-WslBash {
    param([string]$Command)
    if ($DryRun) {
        Write-Host "[dry-run] wsl -d $Distro -- bash -lc `"$Command`""
        return
    }
    & wsl -d $Distro -- bash -lc $Command
}

function Invoke-WslScript {
    param(
        [string]$ScriptText,
        [string[]]$Arguments = @()
    )

    if ($DryRun) {
        $argPreview = ($Arguments -join " ")
        Write-Host "[dry-run] wsl -d $Distro -- bash -s -- $argPreview"
        return
    }

    $ScriptText | & wsl -d $Distro -- bash -s -- @Arguments
}

function Escape-BashSingleQuoted {
    param([string]$Value)
    return ($Value -replace "'", "'""'""'")
}

function Confirm-Execution {
    if ($Yes -or $DryRun) {
        return
    }

    Write-Host ""
    Write-Host "Deployment summary:"
    Write-Host "  Distro:               $Distro"
    Write-Host "  Install mode:         $InstallMode"
    Write-Host "  Gateway port:         $GatewayPort"
    Write-Host "  OpenClaw version:     $OpenClawVersion"
    Write-Host "  Skip onboarding:      $SkipOnboarding"
    Write-Host "  Enable port proxy:    $EnablePortProxy"
    Write-Host ""

    $answer = Read-Host "Continue? [y/N]"
    if ($answer -notin @("y", "Y", "yes", "YES")) {
        throw "Cancelled by user."
    }
}

function Ensure-WslCommand {
    if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
        throw "wsl command not found. Please enable WSL on Windows first."
    }
}

function Ensure-DistroInstalled {
    $distros = Get-WslDistros
    if ($distros -contains $Distro) {
        Write-Step "WSL distro '$Distro' already exists."
        return $true
    }

    Invoke-External "Installing WSL distro '$Distro' (this may require reboot)" {
        wsl --install -d $Distro
    }

    Write-Step "WSL distro install command executed."
    Write-Step "If Windows requested reboot, reboot and rerun this script."
    return $false
}

function Ensure-SystemdEnabled {
    $isEnabled = "no"
    if (-not $DryRun) {
        $isEnabled = (& wsl -d $Distro -- bash -lc "if grep -Eq '^[[:space:]]*systemd[[:space:]]*=[[:space:]]*true[[:space:]]*$' /etc/wsl.conf 2>/dev/null; then echo yes; else echo no; fi").Trim()
    }

    if ($DryRun) {
        Write-Host "[dry-run] Check and enable systemd in /etc/wsl.conf"
        return $true
    }

    if ($isEnabled -eq "yes") {
        Write-Step "systemd is already enabled in /etc/wsl.conf."
        return $true
    }

    Write-Step "Enabling systemd in /etc/wsl.conf (sudo may prompt password)."
    $wslConfScript = @'
set -euo pipefail
sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[boot]
systemd=true
EOF
'@
    Invoke-WslScript -ScriptText $wslConfScript

    Invoke-External "Running wsl --shutdown to apply systemd setting" {
        wsl --shutdown
    }

    Write-Step "systemd setting updated. Re-open WSL and rerun this script."
    return $false
}

function Run-WslInstallScript {
    param([string]$WslScriptPath)

    $scriptContent = Get-Content -Raw -Path $WslScriptPath
    $args = @(
        "--gateway-port", $GatewayPort.ToString(),
        "--install-mode", $InstallMode,
        "--openclaw-version", $OpenClawVersion
    )

    if ($DryRun) {
        $args += "--dry-run"
    }

    Write-Step "Running WSL install script."
    Invoke-WslScript -ScriptText $scriptContent -Arguments $args
}

function Run-Onboarding {
    if ($SkipOnboarding) {
        Write-Step "Skip onboarding enabled. Run 'openclaw onboard --install-daemon' manually in WSL."
        return
    }

    if ($AnthropicApiKey -ne "") {
        Write-Step "Running non-interactive onboarding with provided Anthropic API key."
        $escapedKey = Escape-BashSingleQuoted -Value $AnthropicApiKey
        $onboardScript = @"
set -euo pipefail
export ANTHROPIC_API_KEY='$escapedKey'
openclaw onboard --non-interactive \
  --mode local \
  --auth-choice apiKey \
  --anthropic-api-key "\$ANTHROPIC_API_KEY" \
  --secret-input-mode ref \
  --gateway-port $GatewayPort \
  --gateway-bind loopback \
  --install-daemon \
  --daemon-runtime node \
  --skip-skills
"@
        Invoke-WslScript -ScriptText $onboardScript
        return
    }

    Write-Step "Running interactive onboarding in WSL."
    Invoke-WslBash "openclaw onboard --install-daemon"
}

function Run-Verification {
    if ($SkipOnboarding) {
        Write-Step "Skip verification because onboarding was skipped."
        return
    }

    Write-Step "Running post-onboarding checks."
    Invoke-WslBash "openclaw doctor --non-interactive"
    Invoke-WslBash "openclaw gateway status"
    Invoke-WslBash "openclaw status --all"
}

function Ensure-Administrator {
    if ($DryRun) {
        return
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        throw "Portproxy configuration requires Administrator PowerShell."
    }
}

function Configure-PortProxy {
    if (-not $EnablePortProxy) {
        return
    }

    Ensure-Administrator

    Write-Step "Configuring Windows portproxy for WSL Gateway."

    if ($DryRun) {
        Write-Host "[dry-run] Resolve WSL IP and set netsh portproxy + firewall rule."
        return
    }

    $rawIp = (& wsl -d $Distro -- hostname -I).Trim()
    if ($rawIp -eq "") {
        throw "Failed to resolve WSL IP for distro $Distro."
    }
    $wslIp = ($rawIp -split '\s+')[0]
    if ($wslIp -eq "") {
        throw "Failed to parse WSL IP from: $rawIp"
    }

    netsh interface portproxy delete v4tov4 listenaddress=$PortProxyListenAddress listenport=$PortProxyListenPort | Out-Null
    netsh interface portproxy add v4tov4 listenaddress=$PortProxyListenAddress listenport=$PortProxyListenPort connectaddress=$wslIp connectport=$PortProxyTargetPort | Out-Null

    $ruleName = "OpenClaw WSL Gateway $PortProxyListenPort"
    Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule | Out-Null
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $PortProxyListenPort -Action Allow | Out-Null

    Write-Step "Portproxy configured: $PortProxyListenAddress`:$PortProxyListenPort -> $wslIp`:$PortProxyTargetPort"
    Write-Step "Note: WSL IP changes after restart. Re-run this script or refresh mapping when needed."
}

function Main {
    Ensure-WslCommand
    Confirm-Execution

    if (-not (Ensure-DistroInstalled)) {
        return
    }

    if (-not (Ensure-SystemdEnabled)) {
        return
    }

    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $wslScriptPath = Join-Path $scriptRoot "setup_openclaw_wsl.sh"
    if (-not (Test-Path $wslScriptPath)) {
        throw "WSL setup script not found: $wslScriptPath"
    }

    Run-WslInstallScript -WslScriptPath $wslScriptPath
    Run-Onboarding
    Run-Verification
    Configure-PortProxy

    Write-Step "OpenClaw deployment flow completed."
    Write-Step "Open dashboard from WSL with: openclaw dashboard"
}

Main
