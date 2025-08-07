# DevOps

GCP logging: 基于 [docker gcplogs 驱动](https://github.com/GoogleCloudPlatform/community/blob/master/archived/docker-gcplogs-driver/index.md)

OpenRouter justicezyx@gmail.com 提供

* All services are running on 1 gcp vm (it@sxwl.ai)
  * [GCP VM url](https://console.cloud.google.com/welcome?inv=1&invt=Ab4RWg&project=bustling-pen-sv00q)
  * <img width="3022" height="420" alt="image" src="https://github.com/user-attachments/assets/931abe03-e7c9-4475-bbb0-abb2d2247152" />
  * 定期在该服务器上运行 `docker system prune -a --volumes` 来清楚不用的容器和镜像和挂载卷。
* All services are behind nginx; nginx config: `/etc/nginx/conf.d/sxwl.ai.conf` on the above VM
* nginx provide password protection for internal services
* [Arch diagram feishu source](https://tricorder.feishu.cn/wiki/RjfPw00OKiWKNvk8Ldmc4d2snNc#share-KZGQdQrWSo1eb2xAq6mcLHjfn5c)
  <img width="800" height="468" alt="image" src="https://github.com/user-attachments/assets/acce2ea3-b571-4bd6-8f66-b1eea9796742" />

