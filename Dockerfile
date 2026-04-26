FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    HEALTH_CHECK_PORT=28089

# 创建非root用户（安全最佳实践）
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    build-essential \
    python3-dev \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 升级pip（使用默认PyPI源，适合国际平台）
RUN pip install --upgrade pip

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（优化安装顺序，减少层数）
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY main/ ./main/
COPY start.sh .

# 设置执行权限
RUN chmod +x start.sh

# 更改文件所有者
RUN chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露健康检查端口
EXPOSE ${HEALTH_CHECK_PORT:-28089}

# 定义卷用于日志持久化（可选）
RUN mkdir -p /app/logs && chmod 777 /app/logs

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:${HEALTH_CHECK_PORT:-28089}/health || exit 1

# 启动命令
CMD ["sh", "start.sh"]