# user_privilege

APIs for managing user's privileges:

- Superusers have whatever privileges available to any users
- Subscribed users have defined list of privileges

## Cursor Summary

- 目录用途: 用户权限能力的核心定义与判定逻辑（如订阅用户、超级用户等）。
- 说明: 路由层通过依赖或服务调用此处能力，控制接口的访问/频率/功能开关等。
