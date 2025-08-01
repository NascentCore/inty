# Eval

User name and password to `test.inty.cc` `new.test.inty.cc`

```password
wzy:sxwl6662025!
heartmate:heartmate.inty.cc
```

```bash
# 构建镜像
$ git clone git@github.com:NascentCore/inty-backend.git
$ cd inty-backend/app/static/evaluation
$ docker build --platform linux/amd64 \
    --build-arg REACT_APP_API_BASE_URL=https://dev.inty.sxwl.ai/api/v1 \
    -t registry.cn-beijing.aliyuncs.com/sxwl-ai/inty-frontend:latest .
    
# 上传镜像
$ docker push registry.cn-beijing.aliyuncs.com/sxwl-ai/inty-frontend:latest .

# Use gcp to ssh to gcp vm
sudo docker stop inty-test-new
sudo docker rmi registry.cn-beijing.aliyuncs.com/sxwl-ai/inty-frontend:latest
sudo docker run --rm -d -p 8103:80 --name inty-test-new \
    registry.cn-beijing.aliyuncs.com/sxwl-ai/inty-frontend:latest

# namecheap 上配置域名解析
例：new.test.inty.cc -> 35.186.154.142

# 在服务器上部署
$ sudo docker run -d -p 8103:80  \
    --name inty-test-new \
    registry.cn-beijing.aliyuncs.com/sxwl-ai/inty-frontend:latest
    
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
