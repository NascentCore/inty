# Nginx 配置

## 增加 sxwl.ai 到 inty.cc 内容

**What was done**

- **Certificate**
  - Added a temporary nginx HTTP server block for `sxwl.ai` and `www.sxwl.ai` (port 80, root `/var/www/inty.cc`) so Certbot could complete the HTTP-01 challenge.
  - Reloaded nginx so the temporary block was active.
  - Ran `certbot certonly --webroot -w /var/www/inty.cc -d sxwl.ai` (only `sxwl.ai`; `www.sxwl.ai` failed due to DNS NXDOMAIN).
  - Confirmed certificate written to `/etc/letsencrypt/live/sxwl.ai/` (expires 2026-06-12).

- **Nginx**
  - Removed the temporary HTTP-only server block.
  - Added an HTTPS server block for `sxwl.ai` and `www.sxwl.ai`: same content as inty.cc from `/var/www/inty.cc`, SSL using the new cert, `try_files $uri $uri/ =404`.
  - Added an HTTP server block that redirects `sxwl.ai` and `www.sxwl.ai` to HTTPS (same style as inty.cc).
  - Ran `nginx -t` and `systemctl reload nginx` so the new config is in use.

- **Renewal**
  - Checked that cert renewal is already set up (`certbot.timer` enabled and/or `/etc/cron.d/certbot`), so the sxwl.ai cert will be renewed with the others.

- **Not done (blocked by DNS)**
  - `www.sxwl.ai` was not added to the certificate because there is no A/AAAA record for it; once DNS is set, cert can be expanded with `certbot certonly ... --expand -d sxwl.ai -d www.sxwl.ai`.

## iMate 域名 TLS

iMate dev API 公网入口为 **`dev.imate.sxwl.ai`**（`conf.d/sxwl.ai.conf` 反代 8200；可并列 `dev.imate.inty.cc`）。iMate dev Ops 为 **`dev.ops.imate.inty.cc`**（反代 8201）。**iMate prod API** 为 **`imate.inty.cc`**（反代 **8120**，对应 `imate-prod` / `config.yaml.imate_prod`）；Environment **`imate`** 的 Ops 为 **`ops.imate.inty.cc`**（反代 **8301**），须单独为该主机名签发证书。DNS 指向本机后按 Certbot webroot（`-w /var/www/inty.cc`）分别签发证书，路径与 `ssl_certificate` 一致，再 `nginx -t` / reload。

## 更新 Nginx 配置

可通过 GitHub Actions 部署（手动触发，选择 dev/prod 环境）：[Deploy nginx config (sxwl.ai)](https://github.com/NascentCore/inty/actions/workflows/deploy_nginx_conf.yaml)。

或按以下步骤在服务器上手动更新：

```text
htpasswd:/etc/nginx/.htpasswd # Used by nginx.conf
nginx.conf:/etc/nginx/conf.d/sxwl.ai.conf

ssh inty
pushd inty
# SSH key 已经上传到 github
git pull
popd
sudo cp inty/devops/nginx/conf.d/sxwl.ai.conf /etc/nginx/conf.d/sxwl.ai.conf
sudo systemctl restart nginx
sudo systemctl status nginx
```

打开：

1. <https://app.inty.cc/evaluation>
2. <https://dev.inty.sxwl.ai/evaluation>
3. <https://intellimate.app/>

<img width="2434" height="1290" alt="image" src="https://github.com/user-attachments/assets/775fab70-bce7-4cc6-b9d4-643a6ed328d2" />
