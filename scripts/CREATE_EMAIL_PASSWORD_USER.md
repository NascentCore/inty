# 创建邮箱密码测试用户指南

本文档说明如何在数据库中手动创建带有邮箱密码认证的测试用户。

## 概述

邮箱密码认证用户需要以下关键字段：
- `auth_type`: 必须设置为 `AuthType.EMAIL`
- `email`: 用户的邮箱地址
- `password`: 经过哈希处理的密码（使用 bcrypt）
- `deleted_at`: 必须保持为 `None`，系统会据此判定账号是否有效

## 前置要求

### 必需的导入

```python
from app.core.security import get_password_hash
from app.core.uuid import get_new_user_id
from app.db.base import SessionLocal  # 同步版本
from app.db.session import AsyncSessionLocal  # 异步版本
from app.models.user import AuthType, User
from app.services.user_service import generate_next_readable_id, generate_next_readable_id_sync
```

### 数据库连接

确保数据库配置正确，可以通过 `config.yaml` 或环境变量配置数据库连接。

## 步骤说明

### 方法一：使用异步会话（推荐）

#### 步骤 1: 创建数据库会话

```python
from sqlalchemy.ext.asyncio import AsyncSession

async with AsyncSessionLocal() as db:
    # 后续步骤在此会话中进行
    pass
```

#### 步骤 2: 生成用户标识符

```python
# 生成唯一的用户 ID (格式: user-{ULID})
user_id = get_new_user_id()

# 生成可读的用户 ID (8位数字)
readable_id = await generate_next_readable_id(db)
```

#### 步骤 3: 准备邮箱和密码

```python
import uuid

# 生成测试邮箱（或使用固定邮箱）
test_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
# 或使用固定邮箱: test_email = "testuser@example.com"

# 设置明文密码
test_password = "TestPassword123!"

# 对密码进行哈希处理
hashed_password = get_password_hash(test_password)
```

#### 步骤 4: 创建用户对象

```python
user = User(
    id=user_id,
    readable_id=readable_id,
    auth_type=AuthType.EMAIL,  # 关键：必须设置为 EMAIL
    email=test_email,
    password=hashed_password,  # 使用哈希后的密码
    nickname="Test User",  # 可选
    system_language="en",  # 可选，默认为 "en"
)
```

#### 步骤 5: 保存到数据库

```python
db.add(user)
await db.commit()
await db.refresh(user)  # 刷新以获取数据库生成的字段（如 created_at）
```

### 方法二：使用同步会话

#### 步骤 1-3: 与异步版本相同

```python
from sqlalchemy.orm import Session

db: Session = SessionLocal()
```

#### 步骤 2: 生成可读 ID（同步版本）

```python
readable_id = generate_next_readable_id_sync(db)
```

#### 步骤 4-5: 创建并保存用户（同步版本）

```python
user = User(
    id=user_id,
    readable_id=readable_id,
    auth_type=AuthType.EMAIL,
    email=test_email,
    password=hashed_password,
    nickname="Test User",
    system_language="en",
)

db.add(user)
db.commit()
db.refresh(user)
```

## 完整代码示例

### 异步版本（推荐）

```python
#!/usr/bin/env python3
"""
创建邮箱密码测试用户的完整示例（异步版本）
"""
import asyncio
import sys
import uuid
from pathlib import Path

# 添加项目根目录到路径
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

from app.core.security import get_password_hash
from app.core.uuid import get_new_user_id
from app.db.session import AsyncSessionLocal
from app.models.user import AuthType, User
from app.services.user_service import generate_next_readable_id
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


async def create_email_password_user(
    email: str,
    password: str,
    nickname: str = None,
    system_language: str = "en",
) -> User:
    """
    创建邮箱密码认证用户
    
    Args:
        email: 用户邮箱地址
        password: 明文密码
        nickname: 用户昵称（可选）
        system_language: 系统语言（默认 "en"）
    
    Returns:
        创建的用户对象
    """
    async with AsyncSessionLocal() as db:
        # 检查邮箱是否已存在
        from sqlalchemy import select, and_
        
        stmt = select(User).where(
            and_(User.email == email, User.deleted_at == None)
        )
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            logger.warning(f"User with email {email} already exists")
            return existing_user
        
        # 生成用户标识符
        user_id = get_new_user_id()
        readable_id = await generate_next_readable_id(db)
        
        # 哈希密码
        hashed_password = get_password_hash(password)
        
        # 创建用户对象
        user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=AuthType.EMAIL,
            email=email,
            password=hashed_password,
            nickname=nickname or f"User {user_id[:8]}",
            system_language=system_language,
        )
        
        # 保存到数据库
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Created user: {user.id}, email: {user.email}, readable_id: {user.readable_id}")
        return user


async def main():
    """主函数示例"""
    # 创建测试用户
    user = await create_email_password_user(
        email="testuser@example.com",
        password="TestPassword123!",
        nickname="Test User",
    )
    
    print(f"User created successfully!")
    print(f"User ID: {user.id}")
    print(f"Email: {user.email}")
    print(f"Readable ID: {user.readable_id}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 同步版本

```python
#!/usr/bin/env python3
"""
创建邮箱密码测试用户的完整示例（同步版本）
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
sys.path.insert(0, str(parent_dir))

from app.core.security import get_password_hash
from app.core.uuid import get_new_user_id
from app.db.base import SessionLocal
from app.models.user import AuthType, User
from app.services.user_service import generate_next_readable_id_sync
from loguru import logger
from sqlalchemy.orm import Session


def create_email_password_user(
    email: str,
    password: str,
    nickname: str = None,
    system_language: str = "en",
) -> User:
    """
    创建邮箱密码认证用户（同步版本）
    
    Args:
        email: 用户邮箱地址
        password: 明文密码
        nickname: 用户昵称（可选）
        system_language: 系统语言（默认 "en"）
    
    Returns:
        创建的用户对象
    """
    db: Session = SessionLocal()
    try:
        # 检查邮箱是否已存在
        existing_user = db.query(User).filter(
            User.email == email,
            User.deleted_at == None
        ).first()
        
        if existing_user:
            logger.warning(f"User with email {email} already exists")
            return existing_user
        
        # 生成用户标识符
        user_id = get_new_user_id()
        readable_id = generate_next_readable_id_sync(db)
        
        # 哈希密码
        hashed_password = get_password_hash(password)
        
        # 创建用户对象
        user = User(
            id=user_id,
            readable_id=readable_id,
            auth_type=AuthType.EMAIL,
            email=email,
            password=hashed_password,
            nickname=nickname or f"User {user_id[:8]}",
            system_language=system_language,
        )
        
        # 保存到数据库
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Created user: {user.id}, email: {user.email}, readable_id: {user.readable_id}")
        return user
    finally:
        db.close()


def main():
    """主函数示例"""
    # 创建测试用户
    user = create_email_password_user(
        email="testuser@example.com",
        password="TestPassword123!",
        nickname="Test User",
    )
    
    print(f"User created successfully!")
    print(f"User ID: {user.id}")
    print(f"Email: {user.email}")
    print(f"Readable ID: {user.readable_id}")


if __name__ == "__main__":
    main()
```

## 验证步骤

### 1. 检查用户是否创建成功

```python
# 异步版本
async with AsyncSessionLocal() as db:
    from sqlalchemy import select, and_
    stmt = select(User).where(
        and_(User.email == "testuser@example.com", User.deleted_at == None)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        print(
            f"User found: {user.id}, auth_type: {user.auth_type}, "
            f"is_active: {user.is_active}, deleted_at: {user.deleted_at}"
        )

# 同步版本
db: Session = SessionLocal()
user = db.query(User).filter(
    User.email == "testuser@example.com",
    User.deleted_at == None
).first()

if user:
    print(
        f"User found: {user.id}, auth_type: {user.auth_type}, "
        f"is_active: {user.is_active}, deleted_at: {user.deleted_at}"
    )
db.close()
```

### 2. 测试登录

使用创建的邮箱和密码通过 API 端点进行登录测试：

```bash
curl -X POST "http://localhost:8000/api/v1/auth/google/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123!"
  }'
```

或使用 Python 测试：

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/auth/google/login",
    json={
        "email": "testuser@example.com",
        "password": "TestPassword123!"
    }
)

print(response.json())
```

### 3. 验证密码哈希

```python
from app.core.security import verify_password

# 验证密码是否正确
is_valid = verify_password("TestPassword123!", user.password)
print(f"Password verification: {is_valid}")
```

## 常见问题排查

### 问题 1: 用户无法登录，提示 "Invalid email or password"

**可能原因：**
- `auth_type` 未设置为 `AuthType.EMAIL`
- `deleted_at` 不为 `None`（账号仍被标记为已删除）
- 密码哈希不正确
- 邮箱地址不匹配

**解决方案：**
```python
# 检查用户字段
print(f"auth_type: {user.auth_type}")  # 应该是 AuthType.EMAIL
print(f"is_active: {user.is_active}")  # True 表示 deleted_at 为空
print(f"deleted_at is None: {user.deleted_at is None}")  # 应该是 True
print(f"email: {user.email}")  # 应该与登录时使用的邮箱一致
print(f"password is set: {user.password is not None}")  # 应该有密码哈希

# 验证密码
from app.core.security import verify_password
is_valid = verify_password("your_password", user.password)
print(f"Password valid: {is_valid}")
```

### 问题 2: 邮箱已存在错误

**解决方案：**
- 检查是否有已删除的用户（`deleted_at` 不为 None）
- 使用不同的邮箱地址
- 或更新现有用户的密码

### 问题 3: 数据库连接错误

**解决方案：**
- 检查 `config.yaml` 中的数据库配置
- 确认数据库服务正在运行
- 检查数据库用户权限

### 问题 4: Readable ID 生成失败

**解决方案：**
- 检查数据库序列 `user_readable_id_seq` 是否存在
- 如果序列不存在，系统会回退到随机生成 8 位数字
- 可以手动创建序列：
```sql
CREATE SEQUENCE IF NOT EXISTS user_readable_id_seq START 10000000;
```

## 参考

- 测试用例示例: `tests/app/api/v1/endpoints/test_email_password_login.py:50-77`
- 用户模型定义: `app/models/user.py:40-82`
- 密码哈希函数: `app/core/security.py:39-50`
- 用户服务: `app/services/user_service.py:25-57`
- 登录端点实现: `app/api/v1/endpoints/auth.py:229-298`

## 注意事项

1. **密码安全**: 永远不要在代码中硬编码密码，使用环境变量或配置文件
2. **测试环境**: 仅在测试环境中创建测试用户，不要在生产环境使用
3. **数据清理**: 测试完成后记得清理测试用户，避免数据污染
4. **唯一性**: 确保邮箱地址在系统中唯一（考虑已删除的用户）
5. **密码强度**: 虽然测试环境可以放宽，但建议使用符合安全要求的密码

## 清理测试用户

```python
# 异步版本
async with AsyncSessionLocal() as db:
    from sqlalchemy import select, and_
    stmt = select(User).where(User.email == "testuser@example.com")
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # 软删除
        user.deleted_at = datetime.now(UTC)
        await db.commit()
        # 或硬删除
        # await db.delete(user)
        # await db.commit()

# 同步版本
db: Session = SessionLocal()
user = db.query(User).filter(User.email == "testuser@example.com").first()
if user:
    db.delete(user)
    db.commit()
db.close()
```

