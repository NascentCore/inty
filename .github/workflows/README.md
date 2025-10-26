# 工作流程

## 发布内测轨道AAB

运行[playdebug_release.yaml](https://github.com/NascentCore/inty-app/actions/workflows/playdebug_release.yaml) 上传 AAB 到 Google Play
内部测试轨道。

<img width="860" alt="image" src="https://github.com/user-attachments/assets/e3b5c920-3617-4f89-8f56-bfec0e62af2a" />

然后用adspower指纹浏览器打开[内测轨道](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/tracks/internal-testing)

<img width="860" alt="image" src="https://github.com/user-attachments/assets/abf30b54-311b-460c-a472-586cb25d85c6" />

<img width="860" alt="image" src="https://github.com/user-attachments/assets/a7956951-a72c-4832-b75a-fd32c0cc62c5" />

## 部署模型

<img width="300" height="582" alt="image" src="https://github.com/user-attachments/assets/21feb497-7c80-4601-b292-8134317c3c6e" />

Dev 和 prod 在 GCP 上共享相同的虚拟机。