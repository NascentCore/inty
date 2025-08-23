FROM python:3.12-slim

WORKDIR /

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# https://stackoverflow.com/a/58021389/31283770
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# 复制应用代码
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY start.sh .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["/start.sh"]