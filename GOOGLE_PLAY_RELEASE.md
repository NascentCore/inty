# Google Play Release（发布）

## 重要链接

* [Google Play 内测轨道](https://play.google.com/apps/internaltest/4701704785767590286)
<img width="680" height="1182" alt="image" src="https://github.com/user-attachments/assets/2b01ba6e-9412-4824-bf37-59dbb15b59a4" />

## 向 Play 发布新内测版本（适用于需要 Play 签名后的功能测试，如订阅）

总体流程：运行 github workflow 构建新版本、并上传到 internal testing、发布、打开内测轨道连接、从 Play Store 下载新版本

打开 [playdebug_release.yaml](https://github.com/NascentCore/inty-app/actions/workflows/playdebug_release.yaml)
工作流，运行工作流来推送 AAB。

<img width="480" height="1312" alt="image" src="https://github.com/user-attachments/assets/e4362ecd-7001-4013-91da-4987619f4d59" />

工作流完成后，测试版本的草稿会出现在 [Play Console](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/tracks/internal-testing)；
需要进一步将其进行发布；此时需要使用 AdsPower 指纹浏览器登录 Play 账号（参考[飞书文档指纹浏览器使用指南](https://tricorder.feishu.cn/wiki/WMuAwlr6EiX3RakwidGcLrH7nuY)）

<img width="480" height="1538" alt="image" src="https://github.com/user-attachments/assets/0e9f2098-9717-4532-8d0d-5ee8ea924749" />
<img width="480" height="1790" alt="image" src="https://github.com/user-attachments/assets/80c46bc9-1331-424d-8e94-5dfa5a673c4b" />
<img width="480" height="1784" alt="image" src="https://github.com/user-attachments/assets/3bc763e4-aaf7-4229-98a2-bc565528c409" />

打开 [Play Store 内测轨道连接](https://play.google.com/store/apps/details?id=com.ai.intellimate)，
按照提示直接下载安装、或者升级。

### 疑难问题

由于 version code 采用了 git commit count，老版本可能无法得到足够大的 version code，因此需要手动给 [versionCode 赋值](app/build.gradle.kts)
