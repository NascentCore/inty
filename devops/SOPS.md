# DevOps 日常操作

## 定期清理服务器上的 docker 缓存

```terminal
licairong@dev-instance:~$ docker system prune -a
WARNING! This will remove:
  - all stopped containers
  - all networks not used by at least one container
  - all images without at least one container associated to them
  - all build cache

Are you sure you want to continue? [y/N] y
...
```

## Docker pull 卡住

体现为 docker pull step github workflow 超时

![img_v3_02s4_5190d049-13cf-4553-96c4-1de32d770e7g](https://github.com/user-attachments/assets/09cc0d21-e8e0-4bd6-bf74-5318deadd834)

重启 docker daemon，并确保 docker daemon 重启后正常运行

```terminal
licairong@dev-instance:~$ sudo systemctl restart docker
licairong@dev-instance:~$ sudo systemctl status docker
● docker.service - Docker Application Container Engine
     Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-11-17 05:13:19 UTC; 1min 56s ago
TriggeredBy: ● docker.socket
       Docs: https://docs.docker.com
   Main PID: 1198652 (dockerd)
      Tasks: 49
     Memory: 67.2M
        CPU: 2.159s
     CGroup: /system.slice/docker.service
             ├─1198652 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock
             ├─1198879 /usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 5432 -container-ip 172.17.0.5 -container-port 5432
             ├─1198885 /usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 8100 -container-ip 172.17.0.4 -container-port 8000
             ├─1198902 /usr/bin/docker-proxy -proto tcp -host-ip :: -host-port 5432 -container-ip 172.17.0.5 -container-port 5432
             └─1198907 /usr/bin/docker-proxy -proto tcp -host-ip :: -host-port 8100 -container-ip 172.17.0.4 -container-port 8000
```

## 迁移已有后端数据库到一个新的服务器

大体流程：
1. 初始化数据库 schema
2. 转移数据

### 初始化数据库 schema

1. 准备一个新的 config.yaml.new 文件，修改其 数据库 指向新的数据库实例
2. 使用最新的后端容器镜像，启动 bash
   ```
   docker run -it -v $(pwd)/config.yaml.new:/config.yaml ghcr.io/nascentcore/inty-backend/inty-server:main-dev
   ```
   这个命令会启动后端服务，后端服务启动初期会初始化数据库 schema

### 拷贝数据

```bash
docker run --rm -e PGPASSWORD=<password> --network host postgres:16 pg_dump -h localhost -p 5432 -U postgres -d devdb -Fc >devdb.dump
docker run --rm -e PGPASSWORD=<password> --network host -v $(pwd)/devdb.dump:/devdb.dump postgres:16 pg_restore -h <host> -p 5432 -U postgres -d inty-dev /devdb.dump
```
