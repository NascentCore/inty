<!-- CREATED_BY_AGENT -->

# 2026-08-19：磁盘写满导致 SSH/HTTPS 假死，扩容后恢复

## 现象

公网 `app.inty.cc`、`ops.inty.cc` TCP 能连上但 TLS/HTTP 超时；本机 `ssh inty` 在 banner exchange 超时。ICMP 与 22/80/443 端口探测仍成功。静态站与 API 一并不可用，不像单纯某个容器挂掉。

## 根因

GCE 实例 `prod-intellimate`（boot disk 名仍为 `dev-instance`，100GB）根分区写满。serial console 反复出现 `No space left on device`。用户态（sshd、nginx）accept 连接后无法完成协议。

2026-07-02 把容器日志从 `gcplogs` 改成 Docker 默认 `json-file` 且未做 volume 上限/logrotate，json log 与 journal 把盘吃满。`certbot.timer` 虽启用，续期也因盘满失败（`intellimate.app` 等于 8 月过期）。

## 已执行（2026-08-19）

1. 快照 `prod-intellimate-enospc-20260819`（crash-consistent，未 guest-flush）。
2. 磁盘扩到 200GB；reboot；根分区现约 194G，使用率约 35%。
3. 启动脚本 vacuum journal（约 2.1G）并截断超 50M 的 docker json log。
4. `/tmp/inty-backend-start.sh` 在 reboot 后消失，Docker 把它建成目录，`inty-backend-prod` exit 127。已把仓库 `backend/inty/start.sh` 放到 `/opt/inty-prod/inty-backend-start.sh`，重建容器 bind 该路径；systemd `inty-restore-backend-start-sh.service` 在 Docker 前仍同步一份到 `/tmp`。
5. 写入 `/etc/docker/daemon.json`（`max-size=50m`，`max-file=3`）与 `/etc/logrotate.d/docker-container-json`。daemon.json 要等下次 dockerd 重启才作用于**新**容器；现有容器靠 logrotate 的 `copytruncate`。
6. `certbot renew`：`intellimate.app`、`sxwl.ai` 等成功。`dev.ops.inty.cc` 因证书仍含已无 nginx vhost 的 `dev.ops.imate.inty.cc` 而失败，已用单域名重签。若干无 DNS 的历史域名（`test.inty.cc`、`proxy.sxwl.ai` 等）仍过期，不影响当前入口。

## 恢复后核对（外网）

- `https://app.inty.cc/` 200
- `https://ops.inty.cc/health` 200
- `https://dev.ops.inty.cc/health` 200（TLS 有效）
- `https://intellimate.app/` 200（证书已续）

## 回退

磁盘不可缩回；若新容器异常，可用快照 `prod-intellimate-enospc-20260819` 另挂盘排查。不要 `docker system prune --volumes`（会伤 `inty-pg` 数据）。

完整时间线与 follow-up：[post_mortem/2026-08-19-prod-outage.md](../post_mortem/2026-08-19-prod-outage.md)。Issues：[#3887](https://github.com/NascentCore/inty/issues/3887) [#3888](https://github.com/NascentCore/inty/issues/3888) [#3889](https://github.com/NascentCore/inty/issues/3889) [#3890](https://github.com/NascentCore/inty/issues/3890)。
