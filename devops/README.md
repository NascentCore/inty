# DevOps

* GCP 谷歌云平台，提供文生图等各类后端服务：it@sxwl.ai
  * logging: 基于 [docker gcplogs 驱动](https://github.com/GoogleCloudPlatform/community/blob/master/archived/docker-gcplogs-driver/index.md)
  * All services are running on 1 gcp vm (it@sxwl.ai)
    * [GCP VM url](https://console.cloud.google.com/welcome?inv=1&invt=Ab4RWg&project=bustling-pen-sv00q)
    * <img width="3022" height="420" alt="image" src="https://github.com/user-attachments/assets/931abe03-e7c9-4475-bbb0-abb2d2247152" />
    * 定期在该服务器上运行 `docker system prune -a --volumes` 来清楚不用的容器和镜像和挂载卷。
  * All services are behind nginx; nginx config: `/etc/nginx/conf.d/sxwl.ai.conf` on the above VM
  * nginx provide password protection for internal services
  * [Arch diagram feishu source](https://tricorder.feishu.cn/wiki/RjfPw00OKiWKNvk8Ldmc4d2snNc#share-KZGQdQrWSo1eb2xAq6mcLHjfn5c)
    <img width="800" height="468" alt="image" src="https://github.com/user-attachments/assets/acce2ea3-b571-4bd6-8f66-b1eea9796742" />
* langsmith 监控平台：try@sxwl.ai
* OpenRouter 大模型聚合调用平台：it@sxwl.ai
  * 下面 2 个 API key 应该删除（不知道哪里用到）
  * <img width="800" height="268" alt="image" src="https://github.com/user-attachments/assets/322ef239-ef54-4679-b7e0-441b0025a93c" />
