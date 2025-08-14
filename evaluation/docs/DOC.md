# Eval

* This is a thin wrapper on top of inty backend
* JWT token is hardcoded in api.ts
* The inty backend is configured through env var REACT_APP_API_BASE_URL

Nginx is installed on the server to do login:

* `test.inty.cc` `new.test.inty.cc` share the same password files; there are 2 users:

    ```password
    wzy:sxwl6662025!
    heartmate:heartmate.inty.cc
    ```

Deployment process:

```bash
# 构建镜像
git clone git@github.com:NascentCore/inty-backend.git
cd inty-backend
cd app/static/evaluation
IMAGE=ghcr.io/nascentcore/inty-backend/inty-eval:latest
docker build --push --platform linux/amd64 \
    --build-arg REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1 \
    --tag $IMAGE .

# Use gcp to ssh to gcp vm
ssh inty
docker stop inty-test-new
# You are now on another server, redefine env var
IMAGE=ghcr.io/nascentcore/inty-backend/inty-eval:latest
docker rmi $IMAGE
docker run --rm -d -p 8103:80 --name inty-test-new $IMAGE

# namecheap 上配置域名解析
例：new.test.inty.cc -> 35.186.154.142
    
# 配置 nginx
$ sudo vim /etc/nginx/conf.d/sxwl.ai.conf
# 增加如下配置
server {
    server_name new.test.inty.cc; 
    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8103;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# 申请 tls 证书
$ sudo certbot --nginx -d new.test.inty.cc
```
