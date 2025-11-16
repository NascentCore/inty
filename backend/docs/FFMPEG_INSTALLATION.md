# FFmpeg 安装指南

## 概述

背景动图生成功能需要 FFmpeg 来将视频转换为 AVIF 或 GIF 格式的动图。本文档提供不同环境下的 FFmpeg 安装方法。

## 资源需求

- **磁盘空间**: 约 50-200 MB（取决于编译选项和依赖）
- **运行时内存**: 根据视频大小和复杂度，通常 100MB - 2GB
- **CPU**: 转码是 CPU 密集型任务，多核处理器可显著提升速度
- **依赖**: 需要 libavif 编码器支持（用于 AVIF 格式）

## 安装方法

### macOS

使用 Homebrew 安装（推荐）：

```bash
brew install ffmpeg
```

**重要**: 默认安装的 ffmpeg 可能不包含 libavif 编码器。Homebrew 的新版本不再支持 `--with-*` 选项，需要手动安装依赖并重新编译。

#### 方法 1: 安装 libavif 库（推荐）

```bash
# 安装 libavif 库
brew install libavif

# 重新安装 ffmpeg（会自动检测已安装的 libavif）
brew reinstall ffmpeg
```

#### 方法 2: 从源码编译（如果方法 1 无效）

如果上述方法无效，可能需要从源码编译支持 libavif 的 ffmpeg：

```bash
# 安装依赖
brew install libavif aom

# 下载 FFmpeg 源码
cd /tmp
git clone https://git.ffmpeg.org/ffmpeg.git
cd ffmpeg

# 配置编译选项（启用 libavif）
./configure \
  --prefix=/opt/homebrew \
  --enable-shared \
  --enable-libavif \
  --enable-libaom \
  --enable-gpl \
  --enable-version3

# 编译（使用所有 CPU 核心）
make -j$(sysctl -n hw.ncpu)

# 安装（需要管理员权限）
sudo make install
```

#### 验证安装

```bash
# 检查版本
ffmpeg -version

# 检查是否支持 libavif 编码器
ffmpeg -encoders | grep avif
```

如果输出包含 `libavif`，说明已支持 AVIF 格式。

**注意**: 如果系统不支持 libavif，代码会自动回退到 GIF 格式，功能仍然可以正常使用。

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

验证安装：

```bash
ffmpeg -version
```

### Linux (CentOS/RHEL)

```bash
sudo yum install -y ffmpeg
# 或使用 dnf (较新版本)
sudo dnf install -y ffmpeg
```

### Docker 环境

Dockerfile 中已包含 FFmpeg 安装，无需额外配置：

```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

### Windows

1. 访问 [FFmpeg 官方网站](https://ffmpeg.org/download.html)
2. 下载 Windows 版本
3. 解压到指定目录（如 `C:\ffmpeg`）
4. 将 `bin` 目录添加到系统 PATH 环境变量

验证安装：

```cmd
ffmpeg -version
```

## 验证安装

安装完成后，运行以下命令验证：

```bash
# 检查版本
ffmpeg -version

# 检查是否支持 libavif 编码器（用于 AVIF 格式）
ffmpeg -encoders | grep avif

# 检查是否支持 GIF 编码器
ffmpeg -encoders | grep gif
```

## 常见问题

### 1. FFmpeg 未找到

**错误信息**: `ffmpeg 未安装或不在 PATH 中`

**解决方法**:

- 确保 FFmpeg 已正确安装
- 检查 FFmpeg 是否在系统 PATH 中：`which ffmpeg` (Linux/macOS) 或 `where ffmpeg` (Windows)
- 如果已安装但不在 PATH 中，需要将 FFmpeg 的 `bin` 目录添加到 PATH 环境变量

### 2. 不支持 libavif 编码器

**错误信息**: 转换 AVIF 格式时失败，或日志显示"FFmpeg 不支持 libavif 编码器，将回退到 GIF 格式"

**解决方法**:

- **自动回退**: 代码会自动检测并回退到 GIF 格式，功能仍然可用
- **macOS**:
  - 先安装 `brew install libavif`，然后 `brew reinstall ffmpeg`
  - 如果仍不支持，可能需要从源码编译（见上方安装方法）
- **Linux**: 可能需要从源码编译或使用包含 libavif 的预编译版本
- **Docker**: 默认安装的 ffmpeg 可能不包含 libavif，需要在 Dockerfile 中安装 libavif 开发库并重新编译 ffmpeg

**注意**: 即使不支持 AVIF，系统会自动使用 GIF 格式，不影响功能使用。

### 3. 转换超时

**错误信息**: `视频转换超时`

**解决方法**:

- 检查视频文件大小，过大的文件可能需要更长时间
- 检查系统资源（CPU、内存）是否充足
- 考虑降低输出分辨率或帧率

## 云服务替代方案

如果不想在本地安装 FFmpeg，可以考虑以下云服务方案：

### Google Cloud Functions

使用 Google Cloud Functions 运行 FFmpeg 进行视频转换：

- **优点**: 与现有 GCP 基础设施集成良好，按需付费
- **缺点**: 有执行时间限制，需要处理冷启动
- **成本**: 按调用次数和计算时间计费

### AWS Lambda

使用 AWS Lambda 运行 FFmpeg：

- **优点**: 按需付费，自动扩展
- **缺点**: 执行时间限制（15 分钟），冷启动可能较慢
- **成本**: 按调用次数和计算时间计费

### 第三方视频处理 API

- **Cloudflare Stream**: 如果支持动图转换
- **AWS Elemental MediaConvert**: 功能强大，但可能不支持 AVIF
- **Google Cloud Media Transcoder**: 与 GCP 集成良好

## 相关文档

- [FFmpeg 官方文档](https://ffmpeg.org/documentation.html)
- [libavif 项目](https://github.com/AOMediaCodec/libavif)
