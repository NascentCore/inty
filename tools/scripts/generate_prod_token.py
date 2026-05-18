#!/usr/bin/env python3
"""
使用配置文件中的 secret_key 生成 JWT token

需要先安装依赖:
    pip install python-jose[cryptography] pyyaml

用法:
    python tools/scripts/generate_prod_token.py [--env ENV] [user_id] [expire_days]

环境参数:
    --env ENV    指定环境配置: local, dev, prod (默认: prod)
                 - local: 读取项目根目录的 config.yaml
                 - dev: 读取 devops/config.yaml.dev
                 - prod: 读取 devops/config.yaml.prod

示例:
    # 使用默认环境(prod)、默认用户ID和7天过期时间
    python tools/scripts/generate_prod_token.py

    # 指定环境为 dev
    python tools/scripts/generate_prod_token.py --env dev

    # 指定环境、用户ID和过期天数
    python tools/scripts/generate_prod_token.py --env prod user-01JWZ34Y4D1C92GD86A5R6EWYJ 30

    # 使用 local 环境
    python tools/scripts/generate_prod_token.py --env local user-01JWZ34Y4D1C92GD86A5R6EWYJ 7
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

import cyclopts
import yaml
from jose import jwt


def load_config(env: str) -> dict:
    """根据环境参数加载配置文件"""
    project_root = Path(__file__).parent.parent

    if env == "local":
        config_path = project_root / "config.yaml"
    elif env == "dev":
        config_path = project_root / "devops" / "config.yaml.dev"
    elif env == "prod":
        config_path = project_root / "devops" / "config.yaml.prod"
    else:
        raise ValueError(f"不支持的环境: {env}，支持的环境: local, dev, prod")

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def generate_token(
    user_id: str, secret_key: str, algorithm: str, expire_days: int = 7
) -> str:
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


def main(
    user_id: str = "user-01JWZ34Y4D1C92GD86A5R6EWYJ",
    expire_days: int = 7,
    env: Annotated[
        Literal["local", "dev", "prod"],
        cyclopts.Parameter(name="--env", help="环境配置 (默认: prod)"),
    ] = "prod",
):
    try:
        config = load_config(env)
        security_config = config.get("security", {})
        secret_key = security_config.get("secret_key")
        algorithm = security_config.get("algorithm", "HS256")

        if not secret_key:
            print(f"错误: 配置文件 {env} 中未找到 secret_key", file=sys.stderr)
            sys.exit(1)
    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"错误: 加载配置文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    token = generate_token(user_id, secret_key, algorithm, expire_days)

    print(
        f"生成的 Token (环境: {env}, 用户ID: {user_id}, 过期天数: {expire_days}):"
    )
    print(token)
    print()
    print("可以在 evaluation/start.sh 中使用:")
    print(f'export INTY_API_KEY="{token}"')

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
    cyclopts.run(main)
