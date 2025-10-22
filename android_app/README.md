# AI 驱动的、面向北美年轻男性的亲密体验模拟 Android app（AI-driven intimacy simulation for NA young male adults）

[![Build release APK and AAB](https://github.com/NascentCore/inty-app/actions/workflows/ci.yaml/badge.svg)](https://github.com/NascentCore/inty-app/actions/workflows/ci.yaml)
[![Build and release debug APK](https://github.com/NascentCore/inty-app/actions/workflows/debug_release.yaml/badge.svg)](https://github.com/NascentCore/inty-app/actions/workflows/debug_release.yaml)

```text
IntelliMate: Ultimate companionship, reimagined with AI
Role-play with AI characters.
Create your own IntelliMate, powered by carefully tuned AI agents,
experience your own imagination.
```

## Overview

- Kotlin+Jetpack Compose
- Local development setup: <https://g.co/gemini/share/e068464e9dbd>
- [Daily release for testing](https://github.com/NascentCore/inty-app/releases)
  - 国内手机需要安装 Google 套件才能使用 Google 登录功能
- 将模拟器界面始终置于桌面前方，方便操作观察
  ![image](https://github.com/user-attachments/assets/cbd3f10f-f028-4103-a5f6-c997ba8b9eb9)
- cmd+↑（放大模拟器设备界面）cmd+↓ （缩小模拟器设备界面）
- [adb shell monkey](https://developer.android.com/studio/test/other-testing-tools/monkey)

## Repo 初始化

```bash
git clone git@github.com:NascentCore/inty.git
cd inty/android_app
# 同步 android_app/library/inty_sdk git module
# 不要进入这个目录修改
git submodule update --init --recursive
```

## Key setups

```bash
# Write a new key into the keystore file
keytool -genkeypair -keyalg RSA -keysize 2048 -validity 9125 \
    -keystore sign/intellimate-release-key.jks \
    -storetype JKS \
    -alias <alias of your new key> \
    -storepass <.jks file's password> \
    -keypass <password of your new key>

# Get the fingerprint from the key
keytool -keystore sign/intellimate-release-key.jks -list -v \
    -storepass <.jks file's password> \
    -alias <key alias>
```

Any new key must create an associated OAuth Client ID on Google Cloud.
And added to firebase finger-pints.
Then it can be used to sign the apk/aab to use Sign in with Google.

There are 2 keys used locally: dev, uploading.
The dev key is for general signing during development.
The uploading key is used to sign aab uploaded to Google Play.
Its fingerprint is recorded in Google Play, so Google Play can verify its authenticity.

`app/google-service.json` stores 3 OAuth client IDs, 2 of them are for the above 2 keys,
the last one is associated with Google Play's app signing key.

There are 4 OAuth client IDs created on Google Cloud.
3 of them are associated with the 3 keys above.
1 additional is the web client ID used by backend auth with Android app.
Which is used as `serverClientId`
in [cerdential-manager-siwg](https://developer.android.com/identity/sign-in/credential-manager-siwg).

Google Cloud project and Firebase project is associated through the
`alien-paratext-461204-i9` project ID as well.

![image](https://github.com/user-attachments/assets/1d46e813-d3fd-48bb-adca-90a95691dc69)

## 🏗️ 架构设计

**本机**运行后端，其端口位于`http://localhost:8000`；Android Studio，启动模拟器、或 USB 连接手机；需要使用
`adb` 命令行工具将本地服务端口映射到模拟器、手机上。

```bash
# 列出设备，记录自己使用的设备 ID
adb devices

# 将本机 :8000 端口映射到指定的设备
adb -s <device-id> reverse tcp:8000 tcp:8000
```

然后使用 `local` 构建模式（build type）来启动 App，该构建模式下，`baseUrl()`返回
`http://localhost:8000`。

安装`adb`：`adb`包含在 Android Platform Tools 内，Tools -> SDK Manager，
选择安装 Android SDK Platform Tools；将其路径加入 PATH：

```rc
PATH="/Users/yzhao/Library/Android/sdk/platform-tools:$PATH"
```

![image](https://github.com/user-attachments/assets/47cd8996-afef-41a4-b039-383e5bf167cf)

## 参考

- [Jetpack Compose](https://developer.android.com/jetpack/compose) 用于现代 UI 开发
- 原生Intent导航系统
- [MMKV](https://github.com/Tencent/MMKV) 用于高效存储
- [Coil](https://coil-kt.github.io/coil/) 用于图片加载
- [Firebase](https://firebase.google.com/) 用于后端服务
