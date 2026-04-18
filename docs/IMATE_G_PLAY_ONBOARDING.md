# iMate Android - Google Play 上架计划

本文档仅针对仓库内 **`imate_android_app/`**（包名 **`com.inty.imate`**）。  
**与 `android_app/`（IntelliMate）完全独立**：不同产品、不同包名、不同 Play 应用、不同发布与密钥策略；执行上架时不要混用两套工程的假设或流水线。

---

## 1. 目标与成功标准

- 在 Google Play Console **新建独立应用**（或使用已预留的 `com.inty.imate` 条目），完成素材与政策表单。
- 能稳定产出 **可递增 `versionCode` 的 release AAB**，并通过 CI 或受控环境上传至测试轨道。
- 内测验证通过后，按团队节奏推进 closed / open / production（具体轨道名称以 Console 为准）。

---

## 2. 工程现状（执行前请复核）

以下摘自当前 Gradle 配置，变更后以代码为准。

| 项 | 值 / 说明 |
|----|-----------|
| 模块根目录 | `imate_android_app/` |
| `applicationId` | `com.inty.imate` |
| `namespace` | `com.inty.imate` |
| `minSdk` / `targetSdk` | 29 / 36 |
| `compileSdk` | 36（含 minor 1） |
| ABI | `ndk.abiFilters` 仅 `arm64-v8a` |
| Release | `minify` + `shrinkResources` + `proguard-rules.pro` |
| API 基 URL（`core` BuildConfig.API_BASE_URL） | `debug` → `https://dev.imate.inty.cc/`；`release` → `https://imate.inty.cc/`（与后端部署 GitHub Environment `SERVICE_PUBLIC_URL` 约定一致） |
| 变体 | `debug`、`release` |
| 签名 | 要求 `imate_android_app/sign/imate.jks` 与 `imate_android_app/sign/signing-config.json` 存在，否则配置阶段失败 |
| 版本 | `versionName` 基底为 `"1.0"`，各 build type 带 `versionNameSuffix`（`-{git 短 SHA}-{buildType}`）；`versionCode` 为 `git rev-list --count HEAD`（`gitCommitCount()`），须保证 shallow clone 时仍能解析（CI 已 `fetch-depth: 0`） |
| Git 版本脚本 | `app/build.gradle.kts` 中 `providers.exec` 调用 `git rev-parse` / `git rev-list`，`workingDir` 为仓库根（`rootDir`） |
| AGP | `imate_android_app/gradle/libs.versions.toml` 中为 **alpha** 版本，发布前建议评估是否锁定稳定版 AGP |
| Firebase | 未应用 `google-services` 等插件；若上架需要 Crashlytics/FCM，需另增配置与 `google-services.json` |

参考：`imate_android_app/app/build.gradle.kts`。

---

## 3. Play Console 与账号

- 使用有 **管理员或发布权限** 的开发者账号；确认 **付款资料、开发者协议** 已完成。
- **新建应用**（若尚无）：默认语言、应用名、应用类型（应用 / 游戏）按产品填写。
- 启用 **Play App Signing**：在 Console 中完成上传密钥与 Google 托管签名约定；**上传密钥与 keystore 备份**由团队安全保管，不入公开分支明文。

---

## 4. 密钥与构建机密（仅 iMate）

- **上传密钥**：与 `imate.jks`（或后续替换的 keystore）一致；`signing-config.json` 中的口令不得在仓库中明文长期存放，应迁移到 CI Secrets / 内部密钥管理。
- 确认 CI 或发布机能访问：**keystore 文件** + **各 build type 所需口令**（debug 与 release 在 `signing-config.json` 分 key）。
- 若仓库中缺少 `imate.jks`，需在内部 artifact 或 Secrets 中提供，并文档化路径约定。

---

## 5. 工程侧必做项（iMate 专用）

1. **versionCode**：实现严格单调递增（例如：`git rev-list --count HEAD`、或 `CI_BUILD_NUMBER`、或日期+序号）；每次上架新包必须大于上一版。
2. **versionName**：与产品版本策略对齐；当前 release 带 `-{短 SHA}-release` 等后缀，若上架展示不接受可改为固定 `versionName` 或仅 CI 注入。
3. **Git 元数据**：本地或 CI 须为完整仓库历史（勿用浅克隆导致 `gitCommitCount()` 偏小）；亦可改为纯 CI 注入 `VERSION_CODE` / `VERSION_NAME`。
4. **发布构建命令**：以商店为准使用 **`release`** 变体产出 AAB：`./gradlew :app:bundleRelease`（在 `imate_android_app/` 下执行）。
5. **AGP 稳定性**：评估 alpha AGP 是否可接受；若不能，在 iMate 工程内单独降级/锁定稳定 AGP，**不要**与 `android_app` 共用版本表。
6. **CI**：仓库已有 [.github/workflows/build_and_upload_imate_android.yaml](../.github/workflows/build_and_upload_imate_android.yaml)（`bundleRelease`、上传 `com.inty.imate` Internal testing）；勿与 `android_app` 的 workflow 或 `packageName` 混用。
7. **服务账号**：为 Play 开发者 API 创建 JSON 密钥，授予最小权限（上传 artifact、管理对应应用）；存入 GitHub Secrets 等，变量名由团队自定。

---

## 6. 商店素材与政策（iMate）

按 Google Play 要求准备（清单随政策变化，以 Console 为准）：

- 应用名、短说明、完整说明、图标、截图、功能图（如需要）。
- **内容分级**问卷、**目标地区**与定价。
- **数据安全**表单：根据 iMate 实际收集与传输的数据填写；若后续接入分析/推送，需同步更新。
- **隐私政策 URL**（如适用）。
- AI / 用户生成内容相关声明：以产品与法务结论为准，在 Console 与应用内披露一致。

---

## 7. 技术合规自检

- 对 release **AAB** 使用 Android Studio APK Analyzer 或 `bundletool` 检查 **native `.so`**；若存在，按 Google 对 **16KB 页大小** 等要求验证（以当前政策为准）。
- 核对 **权限列表** 与商店声明、`AndroidManifest` 一致（当前主 manifest 仅 `INTERNET`，后续增权限须同步文档与表单）。
- `allowBackup` 等安全项是否与产品策略一致（当前为 `true`，见 `imate_android_app/app/src/main/AndroidManifest.xml`）。

---

## 8. 发布轨道建议顺序

1. **Internal testing**：先验证安装、升级、关键路径。
2. **Closed testing**：小范围外部测试者。
3. **Open testing**（可选）。
4. **Production**：全量上架。

各轨道使用同一 `applicationId`，通过 **versionCode** 区分版本。

---

## 9. 与 `android_app` 的边界（避免混用）

| 维度 | iMate (`imate_android_app`) | 说明 |
|------|-----------------------------|------|
| 包名 | `com.inty.imate` | Play 应用 ID 不同 |
| 工程目录 | `imate_android_app/` | 独立 Gradle 工程 |
| CI workflow | 需单独或独立 job | 勿改 `android_app` 的 workflow 冒充 iMate |
| 密钥与签名文件 | `imate_android_app/sign/` | 勿使用 IntelliMate 的 keystore |
| 产品文档 | `docs/FR_IMATE_DEVELOPMENT_PLAN.md` 等 | 勿用 IntelliMate 文档代替 iMate 上架决策 |

---

## 10. 执行代理人检查清单（可复制）

- [ ] Play Console 应用已创建，`com.inty.imate` 包名一致。
- [ ] Play App Signing 与上传密钥流程已理清，keystore 备份完成。
- [ ] `versionCode` 已改为可递增且已在 CI/本地验证。
- [ ] `bundleRelease` 在干净环境可成功产出 AAB。
- [ ] 服务账号可成功调用上传 API（或手动上传验证通过）。
- [ ] 数据安全、内容分级、素材、隐私链接已就绪。
- [ ] 内测安装与升级测试通过。
- [ ] 未误用 `android_app` 的包名、密钥或 workflow。

---

## 11. 文件名说明

请求中的文件名 `IMATE_G PLAY_ONBOARDING.md` 在仓库中写为 **`IMATE_G_PLAY_ONBOARDING.md`**（无空格），便于路径与工具引用。
