# CREATED_BY_AGENT
# 构建后端
FROM python:3.12-slim AS base

WORKDIR /
ENV PYTHONPATH=.

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

COPY tools/scripts/requirements.txt scripts_requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r scripts_requirements.txt

FROM base

ARG CONFIG_FILE
ARG INTY_VCS_REVISION=
ARG INTY_BUILD_TIME=
ARG INTY_VCS_DIRTY=false
ENV INTY_VCS_REVISION=${INTY_VCS_REVISION}
ENV INTY_BUILD_TIME=${INTY_BUILD_TIME}
ENV INTY_VCS_DIRTY=${INTY_VCS_DIRTY}
LABEL org.opencontainers.image.revision="${INTY_VCS_REVISION}"

RUN if [ -z "$CONFIG_FILE" ]; then \
    echo "ERROR: CONFIG_FILE build argument is required but not provided" && \
    echo "Usage: docker build --build-arg CONFIG_FILE=path/to/config.yaml -t your-app ." && \
    exit 1; \
fi

# 复制应用代码
COPY app/ app/
COPY backend/ backend/
# companion_harness 在 PYTHONPATH 根目录 import living_sphere / techno_core
COPY living_sphere/ living_sphere/
COPY techno_core/ techno_core/
# Used for manipulate backend system with bundled configurations.
COPY tools/scripts/ tools/scripts/
# 方便操作后端数据库
COPY devops/ devops/
# IntelliMate 使用手册，用来给 IntelliMate 官方助手角色提供回答问题的提示词
COPY docs/INTELLIMATE.md docs/INTELLIMATE.md
# IntelliMate 变更日志，用来给 IntelliMate 官方助手角色提供功能更新提示词
COPY android_app/docs/CHANGE_LOGS.md android_app/docs/CHANGE_LOGS.md
# 启动脚本
COPY backend/inty/start.sh .

# 复制指定的配置文件到 config.yaml
COPY ${CONFIG_FILE} config.yaml

# 暴露端口
EXPOSE 8000

CMD ["/start.sh"]
