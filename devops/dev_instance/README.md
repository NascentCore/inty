# Dev Instance

Dev instance is on GCP, serves all backend services.

* nginx is the reverse proxy
* in front of dev & prod inty backend, inty-eval

The files are placed onto the host in the following paths

```text
htpasswd:/etc/nginx/.htpasswd # Used by nginx.conf
nginx.conf:/etc/nginx/conf.d/sxwl.ai.conf
```
