# Dev Instance

这里记录了生成环境实例的设置

* Dev instance is on GCP, serves all backend services.
* This instance should only run docker images, do not perform any coding or used for other purposes.
* nginx is the reverse proxy
* in front of dev & prod inty backend, inty-eval

The files are placed onto the host in the following paths

```text
htpasswd:/etc/nginx/.htpasswd # Used by nginx.conf
nginx.conf:/etc/nginx/conf.d/sxwl.ai.conf
```
