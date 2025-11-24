# 部署 web

以 `dev.intellimate.app` 为例：

```bash
# 获取新的证书，并更新 nginx 配置文件中与域名相对的配置项
sudo certbot --nginx -d dev.intellimate.app

# 重启 nginx
sudo systemctl reload nginx
sudo systemctl status nginx
```

Google Oauth client ID 位于 GCP console 上：
[Inty Web App](https://console.cloud.google.com/auth/clients/1034291688895-4aajnset4lc3subled86dikpk92hi7hp.apps.googleusercontent.com?project=alien-paratext-461204-i9)
