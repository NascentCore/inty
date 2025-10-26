# Google Play 发布（发布）

## 重要事项

- [Google Play 内部应用共享](https://play.google.com/console/internal-app-sharing)
  使用你的内测Google账户打开该链接，即可上传签名的aab文件。
- [Google Play 内测轨道应用页面](https://play.google.com/store/apps/details?id=com.ai.intellimate&hl=en-US&ah=EmlT1IB-9hWsv_1I4B8Go9FEIFc)
- 须手动升级（[官方文档](https://play.google.com/apps/internaltest/4701704785767590286)表示可以自动升级，但实际上没有效果）
  - 可能与App尚未发布有关
  - ![图片](https://github.com/user-attachments/assets/3d7c05ea-7cd8-406e-9973-f123d06d1671)
- Google Play 允许重复使用版本代码，补充是已经被丢弃的版本
- 发布2个版本：用于支持产品测试的版本（指向 dev ，playdebug 构建类型）、用户上架发布的版本（指向 prod 、release 构建类型）

## 向Play发布新内测版本（适用于需要Play签名后的功能测试，如订阅）

总体流程：运行github工作流程构建新版本、并上传到内测、发布、打开内测轨道连接、从Play Store下载新版本

[playdebug_release.yaml](https://github.com/NascentCore/inty-app/actions/workflows/playdebug_release.yaml)
工作流，运行工作流来发起AAB。

![图片](https://github.com/user-attachments/assets/e4362ecd-7001-4013-91da-4987619f4d59)

工作完成后，测试版本的草稿出现在[Play Console](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/tracks/internal-testing)；需要进一步将其进行发布；此时需要使用AdsPower指纹器浏览登录播放账号（参考[飞书文档指纹浏览器使用指南](https://tricorder.feishu.cn/wiki/WMuAwlr6EiX3RakwidGcLrH7nuY)）！[图片](https://github.com/user-attachments/assets/0e9f2098-9717-4532-8d0d-5ee8ea924749)![图片](https://github.com/user-attachments/assets/80c46bc9-1331-424d-8e94-5dfa5a673c4b)![图片](https://github.com/user-attachments/assets/3bc763e4-aaf7-4229-98a2-bc565528c409)

打开[Play Store内测轨道连接](https://play.google.com/store/apps/details?id=com.ai.intellimate)，
根据提示直接下载安装、或者升级。

###疑难问题

由于版本号采用了 git commit count，老版本可能无法获得足够大的版本号，因此需要手动给 [versionCode 属性](app/build.gradle.kts)

## 手动构建AAB并上传到内测（内部测试）轨道

- 打开 [IntelliMate 发布页面](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/app-dashboard)
- 打开内测轨道上传页面
  <img width="1028" height="1776" alt="image" src="https://github.com/user-attachments/assets/5d0b7b02-027b-4f73-b546-30f121475c24" />
- 上传使用Android studio生成签名过的App Bundle
  ！[图片](https://github.com/user-attachments/assets/e4db0d37-976b-4f42-aaeb-e98c148a3df5)- 上传完成后，如下所示，后续点击下一步即可，最后点击保存并发布！[图片](https://github.com/user-attachments/assets/4a74c6e2-83c7-429e-99a3-cbfdc6fd3963)