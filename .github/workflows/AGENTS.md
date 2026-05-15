# `.github/workflows/`：CI/CD 与定时任务入口

**一句话**：描述 **GitHub Actions 如何构建、上传与部署** 各应用；其中 **legacy IntelliMate Android 工作流处于维护态**，默认避免无任务改动。

## 读者

- 需要发版、调 schedule、或排查「为什么 merge 后没构建」的工程师。

## 能力分组（不按 YAML 逐行复述）

- **Legacy Android**：上传 AAB 到 Play 内测等（维护态；非必要不改）。
- **iMate Android**：PR 上的 **assembleDebug** 门禁；定时或手动 **bundleRelease** 上传 **iMate 包名** 对应的内测轨道。
- **后端与 Ops 部署**：多环境（含 iMate 第二后端实例）通过 **GitHub Environments 变量** 选择容器名、端口与配置变体；细节以 `devops/README.md` 与专项 runbook 为准。
- **外围自动化**：如 Dify 定时任务、用户分析报表 **兜底重算** 等——**补充** 主业务链路而非替代。

## 机密与素材

- **Secrets 名与权限边界** 以各 workflow `env` 块为准；截图式教程易过期，**以 Actions 与控制台当前 UI 为准**。
