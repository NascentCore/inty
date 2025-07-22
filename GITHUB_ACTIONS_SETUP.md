# GitHub Actions 自动发布到 Google Play 配置指南

## 概述

这个配置实现了以下功能：
- 自动构建 Release AAB 包
- 自动上传到 Google Play 内测轨道
- 支持手动触发和标签触发
- 自动创建 GitHub Release
- 构建产物保存

## 必需的 GitHub Secrets 配置

在你的 GitHub 仓库中，需要配置以下 Secrets（Settings → Secrets and variables → Actions）：

⚠️ **重要**：由于 keystore 文件已在代码仓库的 `sign/` 目录中，只需要配置密码信息和服务账号密钥。

### 1. KEYSTORE_PROPERTIES
keystore.properties 文件的完整内容，格式如下：
```
debug.storeFile=sign/key.jks
debug.storePassword=你的调试密钥库密码
debug.keyAlias=你的调试密钥别名
debug.keyPassword=你的调试密钥密码
release.storeFile=sign/my-release-key.jks
release.storePassword=你的发布密钥库密码
release.keyAlias=你的发布密钥别名
release.keyPassword=你的发布密钥密码
```

### 2. GOOGLE_PLAY_SERVICE_ACCOUNT_KEY
Google Play Console 服务账号的 JSON 密钥文件内容

## Google Play Console 配置

### 第一步：启用 Google Play Developer API
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 选择或创建项目
3. 启用 "Google Play Android Developer API"

### 第二步：创建服务账号
1. 在 Google Cloud Console 中，转到 "IAM & Admin" → "Service Accounts"
2. 点击 "CREATE SERVICE ACCOUNT"
3. 填写服务账号名称（如：github-actions-uploader）
4. 创建并下载 JSON 密钥文件

### 第三步：在 Google Play Console 中关联服务账号

**重要**：这一步必须在 **Google Play Console** 完成，不是在 GCP Console！

1. 访问 [Google Play Console](https://play.google.com/console)
2. 寻找以下任一路径（界面可能因版本而异）：
   
   **路径1** - 通过设置：
   - 左侧菜单 → **设置** → **API 访问权限**
   
   **路径2** - 通过应用：
   - 选择你的应用 → **设置** → **API 访问权限**
   
   **路径3** - 如果看不到"API 访问权限"：
   - 寻找 **"用户和权限"**、**"服务账号"** 或 **"开发者 API"**
   
3. **关键操作**：
   - 点击 **"关联项目"** 或 **"Link project"**
   - 选择你在 Google Cloud Console 中创建的项目
   - 在服务账号列表中找到你创建的账号
   - 点击 **"授予访问权限"** 或 **"Grant access"**

4. **授予权限**：
   - ✅ Release management (Admin) - **必需**
   - ✅ Store listing (Admin) - 推荐  
   - ✅ App information (Read only) - 推荐

**🚨 如果完全找不到这些选项**：
可能你的 Google Play 开发者账号还没有完全激活，或者需要先创建一个应用。

### 第四步：应用发布状态说明

**重要理解**：
- 🔄 **自动上传**：GitHub Actions 自动构建并上传 AAB 文件
- 📝 **草稿状态**：上传后创建为草稿状态（status: draft）
- 👤 **手动发布**：需要在 Google Play Console 中手动点击发布

**工作流程**：
1. **自动构建**：GitHub Actions 构建 AAB 文件
2. **自动上传**：上传到 Google Play Console 内测轨道（草稿状态）
3. **手动发布**：登录 Google Play Console，审查并发布到测试用户

**为什么是草稿状态？**
- 新应用或首次发布必须先创建为草稿
- 允许你在 Google Play Console 中审查发布内容
- 确保发布说明、截图等信息完整

## 使用方法

### 自动触发（推荐）
创建并推送标签：
```bash
git tag v1.0.0
git push origin v1.0.0
```

### 手动触发
1. 访问 GitHub 仓库的 Actions 页面
2. 选择 "Build and Deploy to Google Play Internal Testing" workflow
3. 点击 "Run workflow"
4. 选择目标轨道（internal/alpha/beta/production）

## 构建产物

每次构建成功后，以下文件将被保存：
- `app-release.aab`：发布用的 AAB 文件
- `mapping.txt`：ProGuard 混淆映射文件（用于调试崩溃日志）

## 故障排除

### 常见错误及解决方案

#### 1. "Package not found" 错误
- 确保已在 Google Play Console 中手动上传过至少一个版本
- 检查 applicationId 是否与 Google Play 中的包名一致

#### 2. "Insufficient permissions" 错误  
- 检查服务账号是否正确关联到 Google Play Console 项目
- 确认服务账号拥有 "Release management (Admin)" 权限

#### 3. "Invalid keystore" 错误
- 确认 `sign/my-release-key.jks` 和 `sign/key.jks` 文件存在于代码仓库中
- 检查 keystore.properties 中的密码是否正确
- 验证密钥库文件没有损坏

#### 4. 版本号冲突
- **CI环境**：使用Git提交数量作为versionCode，确保每次构建都有唯一版本号
- **本地环境**：使用version.properties文件递增版本号
- 如果仍有冲突，检查Git历史或确认构建环境检测是否正确

#### 5. 发布说明不匹配
- 系统会自动生成带版本号的发布说明到 `distribution/whatsnew-dynamic/` 
- 如果发布说明为空，检查 Git 提交历史是否存在
- 可以通过修改 workflow 中的生成逻辑来自定义内容

## 版本号管理策略

系统采用智能版本号管理，根据环境自动选择策略：

### CI环境（GitHub Actions）
- **基准**：使用 `git rev-list --count HEAD` 获取总提交数量
- **优点**：每次构建都有唯一、递增的版本号
- **最小值**：版本号至少从10开始，避免过小的版本号
- **示例**：如果仓库有45个提交，versionCode = 45

### 本地开发环境
- **基准**：使用 `version.properties` 文件存储版本号
- **递增时机**：执行 release 构建时自动递增
- **持久化**：版本号变更会保存到文件，下次构建继续递增

### 版本号同步
- CI构建的版本号通常比本地更高（基于提交总数）
- 这确保了自动发布不会与本地测试版本冲突
- 如需同步，可以更新本地 `version.properties` 文件

## 高级配置

### 修改发布轨道
默认上传到内测轨道（internal），可通过以下方式修改：
- 手动触发时选择不同轨道
- 修改 workflow 文件中的 `track` 参数

### 自动生成发布说明
系统会自动生成版本特定的发布说明：

**版本信息自动匹配**：
- 自动获取当前构建的 `versionCode` 和 `versionName`
- 根据触发方式生成不同格式的标题

**智能内容生成**：
- **标签触发**：提取从上个标签到当前的所有提交信息
- **手动触发**：提取最近3个提交的信息
- 自动生成中英文双语发布说明
- 包含版本号、构建号和具体变更内容

**备用模板**：
如需自定义模板，可编辑 `distribution/whatsnew/` 目录下的文件：
- `whatsnew-zh-CN`：中文发布说明模板
- `whatsnew-en-US`：英文发布说明模板

**示例输出**：
```
🚀 版本 v1.2.0 (构建 15)

本次更新内容：
• 修复登录状态异常问题
• 优化聊天界面响应速度  
• 新增深色模式支持

✨ 持续改进用户体验
🔧 修复已知问题
```

### 修改发布百分比
**注意**: `userFraction` 参数仅用于正式发布轨道，内测轨道不需要此参数
- 正式发布时可设置：0.05 = 5%, 0.5 = 50%, 1.0 = 100%
- 内测/Alpha/Beta轨道：自动100%发布给测试用户

## 安全注意事项

- 所有敏感信息都通过 GitHub Secrets 管理
- 密钥库文件使用 Base64 编码存储
- 服务账号 JSON 密钥直接存储为 Secret
- 构建过程中创建的临时文件会在构建结束后自动清理

## 监控和日志

- GitHub Actions 提供详细的构建日志
- Google Play Console 显示上传和发布状态
- 使用 GitHub Releases 跟踪版本历史