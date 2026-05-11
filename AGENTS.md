# Inty: 长期情感陪伴 AI

Android Studio 打开`inty/android_app`，详情参考 [android_app/README.md](android_app/README.md)。

后端系统代码位于 `app` 目录（目前正在逐步向 `backend` 目录迁移），参考 [backend/README.md](backend/README.md)。

如果子模块出现脏数据（如下图所示），可以按照下面的流程重置：

![Submodule dirty state screenshot](https://github.com/user-attachments/assets/23852e45-cfe6-4686-9282-c138d40bf96f)

```bash
# 清理子模块的缓存配置
git submodule deinit -f .

# 重新拉取子模块代码
git submodule update --init --recursive

# 使用下面步骤启动后端服务
cp devops/config.yaml.local config.yaml

# 创建虚拟环境供后端 python 代码运行
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 启动 postgres 数据库
docker run --rm --name pg-inty -p 5432:5432 \
  -e POSTGRES_PASSWORD=sxwl666! \
  -e POSTGRES_DB=inty \
  -d postgres:16

# 启动主后端（Android API）
./backend/inty/start.sh --dev

# 启动 ops 平台（evaluation Web UI + ops API，默认 8001）
./backend/ops/start.sh --local
```

本地联调：本地后端+Android Studio App（USB 连接、wifi 连接不支持）指向本地后端

```bash
# 打开 Android Studio
# 选择 debug build type，编译运行
# 然后在 me->settings->backend 选择 local

# 同时打开端口代理、让模拟器可以访问本机端口
# -s 在多个模拟器时可以指向特定模拟器
adb reverse [-s <设备 ID>] tcp:8000 tcp:8000
```
