# Google Cloud Platform部署指南

本文档详细说明如何在 GCP 上创建 VM 实例并部署 Inty 后端进行负载测试。

## 1.环境准备

### 1.1 数据库导出（本地执行）

在开始部署之前，需要从生产环境中导出数据库结构和数据：```bash
# 在本地项目目录执行
cd experimental/locust_test

# 导出完整数据库结构和数据
./export_database.sh --full --init

# 选择性导出指定表
./export_database.sh --tables agents,users,chats,chat_settings --init

# 排除大表
./export_database.sh --exclude-tables logs,audit_logs --init
```**重要提示**：

-确保本地可以连接到生产数据库(127.0.0.1:5432)
-确保本地 pg_dump 版本与服务器 PostgreSQL 版本兼容
- 还原脚本会生成`init.sql`用于测试环境初始化的文件
- 如果无法访问生产环境，则配置脚本会创建基础测试数据
- 生成的init.sql文件包含真实的生产数据，请注意数据安全

### 1.2 GCP 账号和项目设置```bash
# 安装 Google Cloud CLI (如果未安装)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 登录并设置项目
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 启用必要的API
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
```

### 1.2 防火墙规则设置

```bash
# 创建防火墙规则允许测试端口
gcloud compute firewall-rules create inty-test-ports \
    --allow tcp:8000,tcp:8089,tcp:3000,tcp:9090 \
    --source-ranges 0.0.0.0/0 \
    --description "Inty Backend and Locust test ports"

# 如果需要SSH访问
gcloud compute firewall-rules create allow-ssh \
    --allow tcp:22 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow SSH access"
```## 2.创建VM实例

### 2.1 基础VM创建

> **重要提示**：以下命令已修复了镜像版本和磁盘大小警告问题
>
> - 使用最新的 Ubuntu 镜像：`ubuntu-2204-jammy-v20250805`
> - 调整磁盘大小为 20GB 避免警告
> - 统一使用 `asia-southeast1-a` 区域

```bash
# 创建测试VM实例 (4核8GB配置) - 修复版本
gcloud compute instances create inty-load-test-vm \
    --zone=asia-southeast1-a \
    --machine-type=e2-standard-4 \
    --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=http-server,https-server \
    --create-disk=auto-delete=yes,boot=yes,device-name=inty-test-disk,image=projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20250805,mode=rw,size=20,type=projects/$PROJECT_ID/zones/asia-southeast1-a/diskTypes/pd-balanced \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=environment=test,project=inty-backend \
    --reservation-affinity=any
```

### 2.2 高性能配置 (可选)

```bash
# 使用SSD和更高性能的机型 - 修复版本
gcloud compute instances create inty-load-test-vm-hq \
    --zone=asia-southeast1-a \
    --machine-type=c2-standard-4 \
    --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=http-server,https-server \
    --create-disk=auto-delete=yes,boot=yes,device-name=inty-test-disk,image=projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20250805,mode=rw,size=30,type=projects/$PROJECT_ID/zones/asia-southeast1-a/diskTypes/pd-ssd \
    --local-ssd=interface=SCSI \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=environment=test,project=inty-backend
```

### 2.3 获取 VM 信息

```bash
# 获取外部IP地址
gcloud compute instances describe inty-load-test-vm \
    --zone=asia-southeast1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# 查看实例状态
gcloud compute instances list --filter="name=inty-load-test-vm"
```## 3.连接到VM实例

### 3.1 SSH 连接```bash
# 通过gcloud连接
gcloud compute ssh inty-load-test-vm --zone=asia-southeast1-a

# 或使用外部IP直接连接 (需要配置SSH密钥)
ssh -i ~/.ssh/gcp_key ubuntu@EXTERNAL_IP
```

### 3.2 设置 SSH 密钥 (可选)

```bash
# 生成SSH密钥对
ssh-keygen -t rsa -b 4096 -f ~/.ssh/gcp_key

# 将公钥添加到VM
gcloud compute instances add-metadata inty-load-test-vm \
    --zone=asia-southeast1-a \
    --metadata-from-file ssh-keys=~/.ssh/gcp_key.pub
```

## 4. VM 环境配置

### 4.1 系统更新和基础软件安装

```bash
# 连接到VM后执行以下命令
sudo apt update && sudo apt upgrade -y

# 安装必要的软件
sudo apt install -y \
    curl \
    wget \
    git \
    htop \
    docker.io \
    docker-compose \
    python3 \
    python3-pip \
    nginx \
    certbot

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到docker组
sudo usermod -aG docker $USER

# 重新登录以生效
exit
# 重新SSH连接
```### 4.2 Docker Compose 检查```bash
# 现代Docker安装通常包含Compose插件，先检查是否可用
docker compose version

# 如果上述命令有效，则使用新的语法 (推荐)
# docker compose up -d

# 如果需要使用传统的docker-compose命令，检查是否已安装
docker-compose --version

# 仅在docker-compose不可用时才需要手动安装
if ! command -v docker-compose &> /dev/null; then
    echo "安装独立的docker-compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    docker-compose --version
else
    echo "docker-compose 已可用"
fi
```**注意**：

- Ubuntu 22。04 Docker的安装通常包含`docker compose`插件
- 本指南的命令兼容两种语法：`docker-compose` 和 `docker compose`
- 推荐优先使用 `docker compose` (空格分隔)

### 4.3 系统性能优化

```bash
# 调整系统参数以支持高并发
sudo tee -a /etc/sysctl.conf << EOF
# 网络优化
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 5000

# 文件描述符限制
fs.file-max = 65535
EOF

# 应用配置
sudo sysctl -p

# 设置用户限制
sudo tee -a /etc/security/limits.conf << EOF
* soft nofile 65535
* hard nofile 65535
root soft nofile 65535
root hard nofile 65535
EOF
```

## 5. 部署测试环境

### 5.1 代码下载和准备

```bash
# 克隆代码仓库
git clone https://github.com/your-org/inty-backend.git
cd inty-backend

# 切换到测试目录
cd experimental/locust_test

# 创建必要的目录和文件
mkdir -p test-data monitoring/grafana/{dashboards,datasources}
mkdir -p config
```

### 5.2 配置文件准备

````bash
# 配置文件已准备好，直接使用项目中的 config.test.yaml
# 该文件基于生产环境的 config.yaml 调整为测试环境配置
echo "测试配置文件已准备好，包含数据库、日志、安全等所有必要配置"

# 检查必要的密钥文件 (测试环境已提供mock文件)
ls -la inty-backend-key.json inty-firebase-key.json config.test.yaml
echo "✅ 所有必要的配置文件都已准备好"


### 5.3 监控配置

```巴什
#创建Prometheus配置
cat > 监控/prometheus.yml << EOF
全球的：
  刮擦间隔：15s

scrap_configs：
  - 作业名称：'inty-后端'
    静态配置：
      - 目标：['inty-后端：8000']
    指标路径：'/指标'
    刮擦间隔：10s

  - 工作名称：'蝗虫'
    静态配置：
      - 目标：['locust-master:8089']
    指标路径：'/统计/请求'
    刮擦间隔：10s
EOF

#创建Grafana数据源配置
cat > 监控/grafana/datasources/prometheus.yml << EOF
api版本：1
数据源：
  - 姓名：Prometheus
    类型：prometheus
    网址：http://prometheus:9090
    访问：proxy
    是默认值：trueEOF````

## 6. 启动测试环境

### 6.1 启动测试服务

```巴什
#拉取最新的生产镜像
docker pull ghcr.io/nascentcore/inty-backend/inty-server@sha256:e0bbf5278b78326e9ec096b03f94f64

# 启动基础服务
docker-compose -f docker-compose.test.yml up -d postgres

# 初始化表和代理
alembic升级头
卷曲 -X 'POST' \
  'http://localhost:8000/api/v1/auth/google/login' \
  -H '接受：应用程序/json' \
  -H'授权：持有者 eyJhbGciOiJIUZI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTUwody2OTcsInN1YiI6InVzZXItMDFKWVpC VFFWNDMwU1JUMk5XS0pRRFY2WloifQ.CT-CruV4LPBGmkONYXgnpPQ8AxsmAvvkiGL4jKFu9f0' \
  -H '内容类型：应用程序/json' \
  -d'{
  “id_token”：“***”
}'

# 获取到user_id，将nora_agent_insert.sql中agent的创建者user_id替换，并执行


# 启动应用服务（使用生产镜像）docker-compose -f docker-compose.test.yml up -d inty-backend

# 验证服务状态
docker-compose -f docker-compose.test.yml ps
docker-compose -f docker-compose.test.yml 日志 inty-后端```

### 6.2 健康检查

```巴什
# 检查应用健康状态
卷曲 http://localhost:8000/health

# 检查数据库连接
docker-compose -f docker-compose.test.yml exec postgres psql -U postgres -d inty_test -c "选择版本();"

# 测试API端点
卷曲-X POST http://localhost:8000/api/v1/auth/guest \
  -H“内容类型：应用程序/json”\
  -d '{"device_id": "test_device", "nickname": "TestUser"}'```

### 6.3 启动负载测试

```巴什
# 启动Locust测试服务
docker-compose -f docker-compose.test.yml up -d locust-master locust-worker

# 查看Locust状态
docker-compose -f docker-compose.test.yml 日志 locust-master

#访问Locust Web界面
echo "Locust Web UI: http://$(curl -s ifconfig.我）：8089”```

## 7. 执行测试

### 7.1 通过 Web 界面测试

1. 打开浏览器访问: `http://EXTERNAL_IP:8089`
2. 设置测试参数:
   - Number of users: 20
   - Spawn rate: 2 users/second
   - Host: http://inty-backend:8000
3. 点击"Start swarming"开始测试

### 7.2 命令行测试

```巴什
# 基础负载测试
docker-compose -f docker-compose.test.yml exec locust-master \
  蝗虫-f /mnt/locust/locustfile.py \
  --主机=http://inty-backend:8000 \
  --用户=20 \
  --生成率=2 \
  --运行时间=10m \
  --html=/mnt/locust/test-data/basic-load-report.html \
  --csv=/mnt/locust/测试数据/基本负载 \
  --无头

#压力测试
docker-compose -f docker-compose.test.yml exec locust-master \
  蝗虫-f /mnt/locust/locustfile.py \
  --主机=http://inty-backend:8000 \
  --用户=100 \
  --生成率=5 \
  --运行时间=15m \
  --html=/mnt/locust/test-data/stress-test-report.html \
  --csv=/mnt/locust/测试数据/压力测试 \
  --无头```

## 8. 监控和分析

### 8.1 实时监控

```巴什
# 查看集装箱资源使用情况
码头工人统计

# 查看系统资源
顶部

# 查看网络连接
SS-图恩

#查看应用日志
docker-compose -f docker-compose.test.yml 日志 -f inty-backend```

### 8.2 启动监控服务

```巴什
# 启动Prometheus和Grafana
docker-compose -f docker-compose.test.yml --profile 监控 up -d

#访问监控界面
echo "Grafana: http://$(curl -s ifconfig.me):3000 (admin/admin123)"
echo "Prometheus: http://$(curl -s ifconfig.我）：9090”```

### 8.3 数据收集脚本

```巴什
# 创建数据收集脚本
猫 >collect_metrics.sh << 'EOF'
#!/bin/bash
时间戳=$(日期+%Y%m%d_%H%M%S)
REPORT_DIR="测试数据/metrics_$TIMESTAMP"
mkdir -p $REPORT_DIR

# 收集Docker统计信息
docker stats --no-stream > $REPORT_DIR/docker_stats.txt

# 收集系统信息
顶部 -b -n1 > $REPORT_DIR/system_top.txt
自由-h > $REPORT_DIR/memory_usage.txt
df -h > $REPORT_DIR/disk_usage.txt
ss -tuln > $REPORT_DIR/network_connections.txt

# 收集应用日志
docker-compose -f docker-compose.test.yml 日志 --tail=1000 inty-backend > $REPORT_DIR/app_logs.txt

# 数据库查询统计
docker-compose -f docker-compose.test.yml exec -T postgres psql -U postgres -d inty_test -c "SELECT 架构名、表名、n_tup_ins、n_tup_upd、n_tup_del、n_live_tup、n_dead_tup
  来自 pg_stat_user_tables;" > $REPORT_DIR/db_stats.txt

echo "在 $REPORT_DIR 中收集的指标"
EOF

chmod +x 收集指标。嘘```

## 9. 测试结果分析

### 9.1 下载测试报告

```巴什
# 压缩测试数据
tar -czf inty-load-test-results.tar.gz 测试数据/

# 下载到本地（在本地机器执行）
gcloud 计算 scp inty-load-test-vm:~/inty-backend/experimental/locust_test/inty-load-test-results.tar.gz 。--zone=asia-southeast1-a```

### 9.2 生成汇总报告

```巴什
# 报告创建生成脚本
猫 >generate_report.py << 'EOF'
#!/usr/bin/env python3
导入操作系统
导入全局
将 pandas 导入为 pd
导入json
从日期时间导入日期时间

defgenerate_summary_report():
    报告={
        “测试信息”：{
            “时间戳”：datetime.now().isoformat(),
            “环境”：“GCP 虚拟机 4c8g，容器 1c2g”
        },
        “结果”： {}
    }

    #读取CSV结果文件
    csv_files = glob.glob("测试数据/*_stats.csv")
    对于 csv_files 中的 csv_file：
        test_name = os.path.basename(csv_file).replace("_stats.csv", "")
        df = pd.read_csv(csv_file)

        报告[“结果”][测试名称] = {
            "total_requests": df["请求数"].sum(),"failure_rate": df["失败计数"].sum() / df["请求计数"].sum() * 100,
            "avg_response_time": df["平均响应时间"].mean(),
            "max_response_time": df["最大响应时间"].max(),
            "rps": df["请求数/s"].mean()
        }

    # 保存报告
    with open("test-data/summary_report.json", "w") as f:
        json.dump(报告, f, 缩进=2)

    print("生成的摘要报告：test-data/summary_report.json")

如果 __name__ == "__main__":
    生成摘要报告（）
EOF

chmod +x 生成报告.py
python3 生成报告.py```

## 10. 清理资源

### 10.1 停止服务

```巴什
#停止所有服务
docker-compose -f docker-compose.test.yml 下来

#清理Docker资源
docker 系统 prune -f
docker 卷 prune -f```

### 10.2 删除 VM 实例

```巴什
# 删除实例VM
gcloud 计算实例删除 inty-load-test-vm --zone=asia-southeast1-a --quiet

# 删除防火墙规则
gcloud 计算防火墙规则删除 inty-test-ports --quiet```

## 11. 故障排除

### 11.1 GCP 创建实例问题

```巴什
# 问题1：镜像版本过渡警告
# 解决方案：使用最新镜像版本
gcloud 计算映像列表 --project=ubuntu-os-cloud --filter="family=ubuntu-2204-lts" --limit=5

# 问题2: 磁盘大小警告
# 解决方案：使用合适的磁盘大小（20GB对于测试环境足够）
#如果需要更大存储，使用30-50GB

# 问题3：区域不稳定
#确保所有命令使用相同的区域参数：asia-southeast1-a

# 问题4：损耗不足
gcloud 计算 project-info 描述 --format="table(quotas.metric,quotas.usage,quotas.limit)"

# 问题5: 防火墙规则冲突
gcloud 计算防火墙规则列表 --filter="name~inty-test"```

### 11.2 应用常见问题

```巴什
#查看端口占用情况
须藤 netstat -tulpn |查询：8000

#检查Docker日志
docker-compose -f docker-compose.test.yml 日志 inty-backend

# 检查数据库连接
docker-compose -f docker-compose.test.yml 执行 postgres pg_isready -U postgres

# 重启服务
docker-compose -f docker-compose.test.yml 重新启动 inty-后端```

### 11.2 性能调优

```巴什
# 调整Docker内存限制
# 编辑docker-compose.test.yml中的内存限制

# 调整数据库连接池
# 编辑config.test.yaml中的数据库配置

# 调整蝗虫数量
docker-compose -f docker-compose.test.yml up -d --scale locust-worker=4
````

---

**注意事项**：

1.确保GCP项目有足够的损耗和权限
2. 监控测试过程中的成本
3.测试完成后及时清理资源
4. 备份重要测试的数据和报告
5.注意网络安全，不要暴露敏感端口