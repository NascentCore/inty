# 第一阶段：构建前端
FROM node:18-slim AS frontend-builder

WORKDIR /

# 复制前端代码和依赖文件
COPY evaluation/ evaluation/
COPY build_evaluation.sh .

RUN ./build_evaluation.sh

# 第二阶段：构建后端
FROM python:3.12-slim AS base

WORKDIR /

# Check platform compatibility
RUN if [ "$(uname -m)" != "x86_64" ]; then \
    echo "ERROR: This Dockerfile requires AMD64 platform (x86_64) due to animeface dependency" && \
    echo "Current architecture: $(uname -m)" && \
    exit 1; \
fi

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# https://stackoverflow.com/a/58021389/31283770
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

FROM base

ARG CONFIG_FILE

RUN if [ -z "$CONFIG_FILE" ]; then \
    echo "ERROR: CONFIG_FILE build argument is required but not provided" && \
    echo "Usage: docker build --build-arg CONFIG_FILE=path/to/config.yaml -t your-app ." && \
    exit 1; \
fi

# 复制应用代码
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
# Used for manipulate backend system with bundled configurations.
COPY scripts/ scripts/
COPY start.sh .

# 复制指定的配置文件到 config.yaml
COPY ${CONFIG_FILE} config.yaml

# 从前端构建阶段复制构建结果
COPY --from=frontend-builder /app/static/evaluation/ app/static/evaluation/
COPY --from=frontend-builder /app/static/evaluation/resources/ app/static/evaluation/resources/

# 暴露端口
EXPOSE 8000

CMD ["/start.sh"]