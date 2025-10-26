#！/bin/bash -e

DEV=false
# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --dev)
      DEV=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done
# 这是为了在 docker 容器中启动端口服务器。
# 您应该使用 docker compose 在本地启动服务器。
# 运行数据库迁移
echo "Starting database migrations..."
export PYTHONPATH=.
# 初始化管理员用户user-01JWZ34Y4D1C92GD86A5R6EWYJ，此福利预置给用户。
#所有预置角色均由该用户创建。也支持管理系统的登录。
# 只能手动运行下面的命令，因为其与后面的 alembic update head 命令冲突。
# 即：init_admin_user.py 需要用户表存在。所以要先运行 alembic 升级头。
#但alembic升级头需要init_admin_user。py运行完成生成的管理员默认id。
# python 脚本/init_admin_user.py
alembic upgrade head
#初始化订阅计划，读取信息会提供给应用程序向Google Play查询订阅计划详情到参考。
python scripts/init_subscription_plans_simple.py

if [ "$DEV" = true ]; then
  echo "Starting in development mode..."
  python scripts/init_admin_user.py --user-id user-testing --is-superuser false
# ./build_evaluation.嘘
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  echo "Starting in normal mode without reloading..."
  uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
