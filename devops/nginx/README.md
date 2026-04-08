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

为 `dev.imate.inty.cc`、`imate.inty.cc` 配置 DNS 指向本机后，按现有 Certbot webroot 流程签发证书（证书路径需与 `conf.d/sxwl.ai.conf` 中 `ssl_certificate` 一致），再 `nginx -t` / reload。未签发前不要同步含 HTTPS `server` 块的配置，否则 `nginx -t` 会失败。

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
