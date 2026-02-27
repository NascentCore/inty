# devops - 运维文档

- View apk version code and version name: `aapt dump badging android_app/app/build/outputs/apk/debug/app-debug.apk | grep -i versionCode`,
  it should show something like:
  ```
  package: name='com.ai.intellimate' versionCode='3601' versionName='0.4-91c46c68-debug' platformBuildVersionName='16'
  platformBuildVersionCode='36' compileSdkVersion='36' compileSdkVersionCodename='16'
  ```
