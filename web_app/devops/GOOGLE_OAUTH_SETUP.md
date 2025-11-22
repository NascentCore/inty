# Google OAuth 配置指南

## 问题描述

当部署 web_app 后，使用 Google 登录时出现以下错误：

```
Access blocked: Authorization Error
Error 400: origin_mismatch
```

这是因为应用的 JavaScript origin 未在 Google Cloud Console 中注册。

## 解决方案

需要在 Google Cloud Console 中为 OAuth 2.0 客户端添加授权的 JavaScript origin。

### 当前配置信息

- **OAuth Client ID**: `1034291688895-0e5hq72pghd4nihhpmf989ptv0ag1542.apps.googleusercontent.com`
- **应用标识**: `it@sxwl.ai`
- **生产环境域名**:
  - `https://intellimate.app`
  - `https://www.intellimate.app`
- **开发环境**: `http://localhost:8000`

### 配置步骤

1. **访问 Google Cloud Console**
   - 打开 [Google Cloud Console](https://console.cloud.google.com/)
   - 选择项目（应用标识为 `it@sxwl.ai` 的项目）

2. **导航到 OAuth 2.0 客户端设置**
   - 进入 **APIs & Services** > **Credentials**
   - 找到 Client ID 为 `1034291688895-0e5hq72pghd4nihhpmf989ptv0ag1542.apps.googleusercontent.com` 的 OAuth 2.0 客户端
   - 点击该客户端进行编辑

3. **添加授权的 JavaScript origin**
   在 **Authorized JavaScript origins** 部分，添加以下 origin：

   ```
   https://intellimate.app
   https://www.intellimate.app
   http://localhost:8000
   ```

   **注意**：
   - 每个 origin 必须包含协议（`http://` 或 `https://`）
   - 不能包含路径或端口（除了 localhost 开发环境）
   - 不能包含尾随斜杠

4. **添加授权的重定向 URI（如果需要）**
   在 **Authorized redirect URIs** 部分，确保包含：
   ```
   https://intellimate.app
   https://www.intellimate.app
   http://localhost:8000
   ```

5. **保存更改**
   - 点击 **Save** 保存配置
   - 更改可能需要几分钟才能生效

### 验证配置

1. 清除浏览器缓存和 Cookie
2. 访问 `https://intellimate.app` 或 `https://www.intellimate.app`
3. 尝试使用 Google 登录
4. 如果仍然出现错误，等待几分钟后重试（Google 的配置更新可能需要时间）

### 开发环境配置

开发环境使用 `http://localhost:8000`，确保该 origin 也已添加到 Google Cloud Console 中。

### 常见问题

**Q: 为什么需要添加多个域名？**
A: `intellimate.app` 和 `www.intellimate.app` 是两个不同的域名，都需要单独注册。

**Q: 配置保存后多久生效？**
A: 通常立即生效，但有时可能需要等待几分钟。

**Q: 是否需要在代码中修改配置？**
A: 不需要。只需要在 Google Cloud Console 中配置即可，代码中的 Client ID 保持不变。

## 相关文件

- OAuth Client ID 配置：`web_app/src/constants/index.ts`
- Google 登录组件：`web_app/src/components/GoogleLoginModal/index.tsx`
- Nginx 配置：`devops/nginx/conf.d/sxwl.ai.conf`

---
CREATED_BY_AGENT

