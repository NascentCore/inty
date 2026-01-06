# Nginx 配置

## 更新 Nginx 配置

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

1. https://app.inty.cc/evaluation
2. https://dev.inty.sxwl.ai/evaluation
3. https://intellimate.app/

<img width="2434" height="1290" alt="image" src="https://github.com/user-attachments/assets/775fab70-bce7-4cc6-b9d4-643a6ed328d2" />
