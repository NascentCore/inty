# Google Play Release（发布）

## 重要事项

- [Google Play internal app sharing](https://play.google.com/console/internal-app-sharing)
  使用你的内测 Google 账户打开该链接，即可上传签名的 aab 文件。
- [Google Play 内测轨道 App 页面](https://play.google.com/store/apps/details?id=com.ai.intellimate&hl=en-US&ah=EmlT1IB-9hWsv_1I4B8Go9FEIFc)
- 须手动升级（[官方文档](https://play.google.com/apps/internaltest/4701704785767590286)表示可以自动升级，但实际上没有效果）
  - 可能与 App 还未发布有关
  - ![image](https://github.com/user-attachments/assets/3d7c05ea-7cd8-406e-9973-f123d06d1671)
- Google Play 不允许复用 Version Code，即便是已经被丢弃的版本
- 发布 2 个版本：用于支持产品测试的版本（指向 dev 后端，playdebug 构建类型）、用户上架发布的版本（指向 prod 后端、release 构建类型）

## 向 Play 发布新内测版本（适用于需要 Play 签名后的功能测试，如订阅）

总体流程：运行 github workflow 构建新版本、并上传到 internal testing、发布、打开内测轨道连接、从 Play Store 下载新版本

打开 [playdebug_release.yaml](https://github.com/NascentCore/inty-app/actions/workflows/playdebug_release.yaml)
工作流，运行工作流来推送 AAB。

![image](https://github.com/user-attachments/assets/e4362ecd-7001-4013-91da-4987619f4d59)

工作流完成后，测试版本的草稿会出现在 [Play Console](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/tracks/internal-testing)；
需要进一步将其进行发布；此时需要使用 AdsPower 指纹浏览器登录 Play 账号（参考[飞书文档指纹浏览器使用指南](https://tricorder.feishu.cn/wiki/WMuAwlr6EiX3RakwidGcLrH7nuY)）

![image](https://github.com/user-attachments/assets/0e9f2098-9717-4532-8d0d-5ee8ea924749)
![image](https://github.com/user-attachments/assets/80c46bc9-1331-424d-8e94-5dfa5a673c4b)
![image](https://github.com/user-attachments/assets/3bc763e4-aaf7-4229-98a2-bc565528c409)

打开 [Play Store 内测轨道连接](https://play.google.com/store/apps/details?id=com.ai.intellimate)，
按照提示直接下载安装、或者升级。

### 疑难问题

由于 version code 采用了 git commit count，老版本可能无法得到足够大的 version code，因此需要手动给 [versionCode 赋值](app/build.gradle.kts)

## 手动构建 AAB 并上传到内测（Internal Testing）轨道

- 打开 [IntelliMate 发布页面](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/app-dashboard)
- 打开内测轨道上传页面
  <img width="1028" height="1776" alt="image" src="https://github.com/user-attachments/assets/5d0b7b02-027b-4f73-b546-30f121475c24" />
- 上传使用 Android studio 生成签名过的 App Bundle
  ![image](https://github.com/user-attachments/assets/e4db0d37-976b-4f42-aaeb-e98c148a3df5)
- 上传完成后，如下所示，后续点击下一步即可，最后点击 Save and Publish
  ![image](https://github.com/user-attachments/assets/4a74c6e2-83c7-429e-99a3-cbfdc6fd3963)
