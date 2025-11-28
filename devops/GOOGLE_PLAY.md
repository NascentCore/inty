# Google Play 商店操作运营

为审查员创建超级用户来测试 app 新版本

```bash
docker exec -it inty-backend-dev bash
export PYTHONPATH=.
python scripts/create_email_password_superuser.py --help
python scripts/create_email_password_superuser.py --email test.intellimate@gmail.com --password test.intellimate.666!
```
