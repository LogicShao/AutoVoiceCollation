# ================================
# AutoVoiceCollation Dockerfile
# ================================
# 构建阶段：使用官方 PyTorch 镜像作为基础
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# 使用清华大学镜像源（加速国内访问）
# 如果清华源也有问题，可以尝试：
# - 阿里云：mirrors.aliyun.com
# - 中科大：mirrors.ustc.edu.cn
# - 网易：mirrors.163.com
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list

# 安装系统依赖（FFmpeg 和其他必需工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    wget \
    curl \
    build-essential \
    libsndfile1 \
    fonts-wqy-zenhei \
    fonts-noto-cjk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用清华大学镜像源（加速安装）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn

# 升级 pip
RUN pip install --upgrade pip setuptools wheel

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .

# 安装 Python 依赖
# 注意：PyTorch 已经包含在基础镜像中，这里安装其他依赖
RUN pip install -r requirements.txt

# 可选：如果需要 ONNX Runtime GPU 支持，取消下面的注释
# RUN pip install onnxruntime-gpu>=1.20.0

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /app/out \
    /app/download \
    /app/temp \
    /app/logs \
    /app/models

# 暴露 Gradio 默认端口
EXPOSE 7860

# 设置启动命令
CMD ["python", "webui.py"]
