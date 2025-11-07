# Docker 部署指南

## 📦 快速开始

### 前置要求

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **（可选）NVIDIA Docker**: 用于 GPU 加速

#### 安装 Docker

**Linux (Ubuntu/Debian):**

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 将当前用户加入 docker 组（避免每次使用 sudo）
sudo usermod -aG docker $USER
newgrp docker
```

**Windows/macOS:**

- 下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

#### 安装 NVIDIA Docker（GPU 加速，可选）

如果你有 NVIDIA GPU 并希望使用 GPU 加速：

```bash
# 安装 NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 验证 GPU 是否可用
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

---

## 🚀 部署步骤

### 1. 准备配置文件

首先，创建 `.env` 配置文件：

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑配置文件，填入你的 API Keys
nano .env  # 或使用其他编辑器
```

**最小配置示例 (`.env`):**

```env
# 至少配置一个 API Key（根据你要使用的 LLM 服务）
DEEPSEEK_API_KEY=sk-your-key-here
# 或
GEMINI_API_KEY=your-gemini-key-here
# 或
DASHSCOPE_API_KEY=your-dashscope-key-here
# 或
CEREBRAS_API_KEY=your-cerebras-key-here

# 基本配置
OUTPUT_DIR=./out
DOWNLOAD_DIR=./download
TEMP_DIR=./temp
LOG_DIR=./logs
MODEL_DIR=./models

# ASR 模型
ASR_MODEL=paraformer

# LLM 服务（根据你的 API Key 选择）
LLM_SERVER=Cerebras:Qwen-3-235B-Instruct

# 设备配置（Docker 中自动检测）
DEVICE=auto
```

### 2. 构建并启动服务

#### 方式 A: 使用 GPU（推荐，性能更好）

```bash
# 构建镜像
docker compose build

# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f
```

#### 方式 B: 仅使用 CPU

```bash
# 启动 CPU 版本
docker compose --profile cpu-only up -d

# 查看日志
docker compose logs -f autovoicecollation-webui-cpu
```

#### 方式 C: 快速启动（一键构建并启动）

```bash
# GPU 版本
docker compose up -d --build

# CPU 版本
docker compose --profile cpu-only up -d --build
```

### 3. 访问 WebUI

启动成功后，在浏览器中访问：

- **GPU 版本**: http://localhost:7860
- **CPU 版本**: http://localhost:7861

---

## 📋 常用命令

### 服务管理

```bash
# 启动服务
docker compose up -d

# 停止服务
docker compose down

# 重启服务
docker compose restart

# 查看运行状态
docker compose ps

# 查看日志（实时）
docker compose logs -f

# 查看特定服务的日志
docker compose logs -f autovoicecollation-webui

# 进入容器内部（调试用）
docker compose exec autovoicecollation-webui bash
```

### 镜像管理

```bash
# 重新构建镜像（代码更新后）
docker compose build --no-cache

# 删除旧镜像
docker image prune -f

# 查看镜像大小
docker images | grep autovoicecollation
```

### 数据管理

```bash
# 清理输出目录
rm -rf ./out/*

# 清理下载目录
rm -rf ./download/*

# 清理临时文件
rm -rf ./temp/*

# 备份模型缓存
tar -czf models-backup.tar.gz ./models/
```

---

## ⚙️ 高级配置

### 自定义端口

编辑 `docker-compose.yml`，修改端口映射：

```yaml
ports:
  - "8080:7860"  # 将 WebUI 映射到主机的 8080 端口
```

### 使用自定义模型目录

```yaml
volumes:
  - /path/to/your/models:/app/models  # 使用自定义模型目录
```

### 限制 GPU 使用

仅使用特定 GPU：

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          device_ids: [ '0' ]  # 仅使用 GPU 0
          capabilities: [ gpu ]
```

### 内存限制

限制容器内存使用：

```yaml
deploy:
  resources:
    limits:
      memory: 16G  # 限制最大 16GB 内存
    reservations:
      memory: 8G   # 预留 8GB 内存
```

---

## 🔧 故障排除

### 0. 网络连接问题（最常见）⭐

**错误信息:**

```
Connection failed [IP: 91.189.91.81 80]
500 reading HTTP response body: unexpected EOF
E: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/jammy-backports/InRelease
```

**原因:** Ubuntu 官方源连接失败，在中国大陆地区很常见。

**解决方案:**

✅ **已集成解决方案**：我们已经在 `Dockerfile` 中集成了阿里云镜像源，直接重新构建即可：

```bash
# 清理构建缓存
docker builder prune -f

# 重新构建
docker compose build --no-cache

# 或使用启动脚本
.\docker-start.bat build
.\docker-start.bat start
```

**如果仍然失败**，请查看详细的网络问题解决方案：[DOCKER_NETWORK_FIX.md](DOCKER_NETWORK_FIX.md)

该文档包含：

- 多种镜像源切换方案（阿里云、清华、中科大）
- 代理配置方法
- Docker 镜像加速器配置
- 完整的故障排除步骤

### 1. 端口已被占用

**错误信息:**

```
Error: bind: address already in use
```

**解决方案:**

```bash
# 查看占用端口的进程
sudo lsof -i :7860

# 修改 docker-compose.yml 中的端口映射
ports:
  - "7861:7860"  # 使用其他端口
```

### 2. GPU 不可用

**错误信息:**

```
Could not find GPU device
```

**解决方案:**

```bash
# 1. 验证 nvidia-docker 是否正确安装
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# 2. 如果失败，重新安装 nvidia-docker
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 3. 或者使用 CPU 版本
docker compose --profile cpu-only up -d
```

### 3. 模型下载慢或失败

**问题:** FunASR 模型下载速度慢

**解决方案:**

```bash
# 方式 1: 手动下载模型到 ./models 目录
# 然后在 .env 中设置 MODEL_DIR=./models

# 方式 2: 使用国内镜像（如果可用）
# 在容器内设置镜像源

# 方式 3: 挂载预先下载的模型
docker compose exec autovoicecollation-webui bash
# 在容器内手动下载模型
```

### 4. 权限问题

**错误信息:**

```
Permission denied: '/app/out'
```

**解决方案:**

```bash
# 修改目录权限
chmod -R 777 ./out ./download ./temp ./logs ./models

# 或者在 Dockerfile 中添加用户权限配置
```

### 5. 内存不足（OOM）

**错误信息:**

```
CUDA out of memory
```

**解决方案:**

1. **降低批处理大小**: 在 `.env` 中设置更小的批处理大小
2. **使用 CPU 版本**: `docker compose --profile cpu-only up -d`
3. **启用 ONNX**: 在 `.env` 中设置 `USE_ONNX=true`

### 6. 日志查看

```bash
# 实时查看日志
docker compose logs -f

# 查看最近 100 行日志
docker compose logs --tail=100

# 导出日志到文件
docker compose logs > docker-logs.txt
```

---

## 📊 性能优化

### 1. 使用 ONNX Runtime

在 `.env` 中启用 ONNX：

```env
USE_ONNX=true
ONNX_PROVIDERS=CUDAExecutionProvider,CPUExecutionProvider
```

修改 `Dockerfile`，取消注释：

```dockerfile
# 安装 ONNX Runtime GPU
RUN pip install onnxruntime-gpu>=1.20.0
```

### 2. 模型缓存优化

挂载本地模型缓存，避免重复下载：

```yaml
volumes:
  - ~/.cache/modelscope:/root/.cache/modelscope  # ModelScope 缓存
  - ~/.cache/huggingface:/root/.cache/huggingface  # HuggingFace 缓存
```

### 3. 使用多阶段构建减小镜像体积

创建 `Dockerfile.optimized`:

```dockerfile
# 构建阶段
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime as builder
WORKDIR /app
COPY ../requirements.txt .
RUN pip install --user -r requirements.txt

# 运行阶段
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY .. .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "webui.py"]
```

---

## 🌐 生产环境部署建议

### 1. 使用反向代理（Nginx）

**nginx.conf 示例:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（Gradio 需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. 使用 HTTPS

```bash
# 使用 Certbot 获取免费 SSL 证书
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. 配置日志轮转

创建 `/etc/logrotate.d/autovoicecollation`:

```
/path/to/AutoVoiceCollation/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### 4. 设置自动重启

在 `docker-compose.yml` 中已包含 `restart: unless-stopped`，确保容器崩溃后自动重启。

### 5. 监控和告警

使用 Docker stats 监控资源使用：

```bash
# 实时监控
docker stats autovoicecollation-webui

# 导出监控数据
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" > stats.txt
```

---

## 🔒 安全建议

1. **不要提交 `.env` 文件到 Git**（已在 `.gitignore` 中）
2. **定期更新镜像**: `docker compose pull && docker compose up -d`
3. **使用 secrets 管理敏感信息**（生产环境）
4. **限制容器权限**: 避免使用 `--privileged` 标志
5. **定期备份数据**: 使用卷快照或定期导出数据

---

## 📝 更新项目

当项目代码更新后：

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker compose build --no-cache

# 3. 重启服务
docker compose down
docker compose up -d

# 4. 验证服务状态
docker compose ps
docker compose logs -f
```

---

## 🆘 获取帮助

如果遇到问题：

1. **查看日志**: `docker compose logs -f`
2. **检查容器状态**: `docker compose ps`
3. **进入容器调试**: `docker compose exec autovoicecollation-webui bash`
4. **提交 Issue**: https://github.com/LogicShao/AutoVoiceCollation/issues

---

## 📚 相关资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [NVIDIA Docker 文档](https://github.com/NVIDIA/nvidia-docker)
- [Gradio 文档](https://www.gradio.app/)
- [AutoVoiceCollation 项目主页](https://github.com/LogicShao/AutoVoiceCollation)

---

## 📄 许可证

本项目遵循原项目的许可证。详见 [LICENSE](LICENSE) 文件。
