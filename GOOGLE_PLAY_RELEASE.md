# Google Play Release（发布）

## 流程

1. 创建新的 tag
2. 运行 github workflow 构建新版本、并上传到 internal testing
3. 由于 version code 采用了 git commit count，老版本可能无法得到足够大的 version code，因此需要手动给 [versionCode 赋值](app/build.gradle.kts)
