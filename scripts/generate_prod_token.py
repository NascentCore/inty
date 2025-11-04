#!/usr/bin/env python3
"""
使用 config.yaml.prod 中的 secret_key 生成 JWT token

需要先安装依赖:
    pip install python-jose[cryptography]

用法:
    python scripts/generate_prod_token.py [user_id] [expire_days]

示例:
    # 使用默认用户ID和7天过期时间
    python scripts/generate_prod_token.py

    # 指定用户ID
    python scripts/generate_prod_token.py user-01JWZ34Y4D1C92GD86A5R6EWYJ

    # 指定用户ID和过期天数
    python scripts/generate_prod_token.py user-01JWZ34Y4D1C92GD86A5R6EWYJ 30
"""

import sys
from datetime import datetime, timedelta

try:
    from jose import jwt
except ImportError:
    print("错误: 需要安装 python-jose 库")
    print("请运行: pip install python-jose[cryptography]")
    sys.exit(1)


def generate_token(user_id: str, secret_key: str, algorithm: str, expire_days: int = 7) -> str:
    """生成 JWT token"""
    expire = datetime.utcnow() + timedelta(days=expire_days)
    
    to_encode = {
        "exp": int(expire.timestamp()),
        "sub": user_id,
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        secret_key,
        algorithm=algorithm,
    )
    
    return encoded_jwt


def main():
    # 从 config.yaml.prod 读取配置
    # secret_key: "893-ac77-4b6d-b644"
    # algorithm: "HS256"
    # access_token_expire_minutes: 10080 (7天)
    secret_key = "893-ac77-4b6d-b644"
    algorithm = "HS256"
    default_expire_days = 7
    
    # 解析命令行参数
    user_id = "user-01JWZ34Y4D1C92GD86A5R6EWYJ"  # dev 环境使用的默认用户ID
    expire_days = default_expire_days
    
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    if len(sys.argv) > 2:
        expire_days = int(sys.argv[2])
    
    # 生成 token
    token = generate_token(user_id, secret_key, algorithm, expire_days)
    
    print(f"生成的 Token (用户ID: {user_id}, 过期天数: {expire_days}):")
    print(token)
    print()
    print("可以在 evaluation/start.sh 中使用:")
    print(f'export INTY_API_KEY="{token}"')
    
    # 验证 token 可以解码
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        print()
        print("Token 验证成功:")
        print(f"  用户ID: {payload.get('sub')}")
        print(f"  过期时间: {datetime.fromtimestamp(payload.get('exp'))} (UTC)")
    except Exception as e:
        print(f"Token 验证失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

