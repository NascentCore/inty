# Google Play 商店操作运营

为审查员创建超级用户来测试 app 新版本，目前 Email 密码组合为：

- intellimate@gmail.com
- intellimate

```bash
docker exec -it inty-backend-dev bash
export PYTHONPATH=.
python scripts/create_email_password_user.py --help
python scripts/create_email_password_user.py --email <email> --password <password>

# 如需删除账户
psql -h localhost -U postgres -d inty
inty=# delete from users where email = 'test@gmail.com';
```

<img width="800" height="1382" alt="image" src="https://github.com/user-attachments/assets/95551723-8001-43e5-a93d-0a998496d5e7" />
