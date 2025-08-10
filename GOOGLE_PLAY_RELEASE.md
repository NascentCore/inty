# Google Play Release（发布）

## 重要链接

* [Google Play 内测轨道 App 页面](https://play.google.com/store/apps/details?id=com.ai.intellimate&hl=en-US&ah=EmlT1IB-9hWsv_1I4B8Go9FEIFc)
* 须手动升级（[官方文档](https://play.google.com/apps/internaltest/4701704785767590286)表示可以自动升级，但实际上没有效果）
  * 可能与 App 还未发布有关
  * <img width="480" height="1512" alt="image" src="https://github.com/user-attachments/assets/3d7c05ea-7cd8-406e-9973-f123d06d1671" />

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

## 手动构建 AAB 并上传到内测（Internal Testing）轨道

* 检查最近一次 release version code
  * <img width="680" height="1364" alt="image" src="https://github.com/user-attachments/assets/96a4bc1c-a4d9-423a-b7a7-f8b17dd71393" />
* 更新 app/build.gradle.kts 内的 version code 到最近一次 release version code +1，如上图所示，应该将 version code 改为 349
  * 此改动不应该提交
  * <img width="3022" height="820" alt="image" src="https://github.com/user-attachments/assets/5e79445e-3693-4d41-b419-9287d91214b6" />
* 使用 Android studio 生成签名过的 App Bundle
  * <img width="960" height="1400" alt="image" src="https://github.com/user-attachments/assets/e4db0d37-976b-4f42-aaeb-e98c148a3df5" />
* 使用 Bundletool 确认 version code：`bundletool dump manifest --bundle app/release/app-release.aab | grep versionCode`
  * 应显示上面设置的 versioncode
  * <img width="3020" height="254" alt="image" src="https://github.com/user-attachments/assets/9f69ba9d-9ef0-41e5-92ef-0d6eeba56fee" />
* 打开 Google Play Console 上传刚刚构建的 AAB 文件，注意确认路径正确
  * 首先，点击创建新的版本
    * <img width="680" height="1400" alt="image" src="https://github.com/user-attachments/assets/32672101-5a56-4266-a600-af479c335694" />
  * 然后，点击上传
    * <img width="680" height="1772" alt="image" src="https://github.com/user-attachments/assets/9a3028f8-7881-4c55-8f03-0e25606724bd" />
    * <img width="680" height="1126" alt="image" src="https://github.com/user-attachments/assets/76041017-8aa7-4d73-8732-c1cbd9df8b0f" />
  * 上传完成后，如下所示，后续点击下一步即可
    * <img width="680" height="1728" alt="image" src="https://github.com/user-attachments/assets/48e12f83-eaa2-418a-be90-630b8e14ebee" />
    * <img width="680" height="1784" alt="image" src="https://github.com/user-attachments/assets/4a74c6e2-83c7-429e-99a3-cbfdc6fd3963" />



