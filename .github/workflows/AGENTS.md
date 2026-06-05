# `.github/workflows/`：CI/CD 与定时任务入口

**legacy IntelliMate Android 工作流处于维护态**，默认避免无任务改动。

## 能力分组（不按 YAML 逐行复述）

- **Legacy Android**：上传 AAB 到 Play 内测等（维护态；非必要不改）。
- **iMate Android**：PR 上的 **assembleDebug** 门禁；定时或手动 **bundleRelease** 上传 **iMate 包名** 对应的内测轨道。
- **后端与 Ops 部署**：多环境（含 iMate 第二后端实例）通过 **GitHub Environments 变量** 选择容器名、端口与配置变体；细节以 `devops/README.md` 为准。
- **外围自动化**：如 Dify 定时任务；**IntelliMate 用户分析日报**（`daily_intellimate_user_activity_report.yaml`，生产主路径，push worker 默认不跑日报）等——**补充** 主业务链路而非替代。
