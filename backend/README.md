# InTy 后端服务

## 本地启动后端服务

```bash
# 启动数据库服务
docker run --rm --name pg-vec-inty -p 5432:5432 \
   -e POSTGRES_PASSWORD=sxwl666! -e POSTGRES_DB='inty' -d pgvector/pgvector:pg16

# 安装后端 Python 服务依赖
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 安装后端服务配置
cp devops/config.yaml.test config.yaml
./start.sh --dev
```

## 更新 openapi.json【已计划废弃】

```bash
# 调用脚本更新 app/openapi.json
export PYTHONPATH=.
python scripts/generate_openapi_json.py

# 根据 app/openapi.json 更新 app/stainless.yml
# 包括增加新的 API endpoint、删除 openapi.json 中被删除的 API endpoint 等等
```

然后，创建 Pull Request，等待 app.stainless.com 启动更新

<img width="480" height="932" alt="image" src="https://github.com/user-attachments/assets/5ba171a1-c387-404d-9ab2-c81c1c85ef74" />

## GCS 配置

GCS public access

<img width="800" alt="image" src="https://github.com/user-attachments/assets/9230dc1f-1430-467b-b12e-bfba1def3922" />

获取 GCP 凭证密钥 JSON 文件以允许后端访问 GCS buckets：

<img width="3018" height="1218" alt="image" src="https://github.com/user-attachments/assets/df5c7bfb-b4ad-4d0a-b4cb-65b25c7d4560" />

## 部署

详情查看：.github/workflows/build_and_deploy_backend.yml

## 服务帐号密钥生成

配置文件中需要配置 GCS 和 FireBase 的服务帐号密钥

### Firebase 服务账号密钥生成

1. 进入 Firebase Console：
   - 访问 <https://console.firebase.google.com/>
   - 选择项目（Inty）

2. 生成服务账号密钥：
   - 在项目设置 -> 服务账号 -> 生成新的私钥
   - 下载的文件重命名为：inty-firebase-key.json

### Google Cloud Storage 服务账号密钥生成

1. 进入 Google Cloud Console：
   - 访问 <https://console.cloud.google.com/>
   - 选择项目（Inty）

2. 创建服务账号（service account）：
   - 设置 "roles/storage.admin" 角色
   - 点击创建的服务帐号 -> 密钥 -> 创建新密钥
   - 下载的文件重命名为：inty-backend-key.json
