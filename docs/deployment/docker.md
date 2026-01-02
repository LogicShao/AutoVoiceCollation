# Docker 部署指南

> ✅ 项目版本：v2.0 | 支持 GPU/CPU 双模式部署，一键启动，适合新手与生产环境

---

## 📦 快速开始

### 已创建的文件

本次为 `AutoVoiceCollation` 项目创建了完整的 Docker 部署方案，包含以下核心文件：

#### 核心文件
1. **`Dockerfile`** — GPU 版本镜像配置  
   - 基于 `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime`  
   - 内置 FFmpeg 和系统依赖  
   - 支持 GPU 加速
2. **`Dockerfile.cpu`** — CPU 版本镜像配置  
   - 基于 `python:3.11-slim`  
   - 适用于无 GPU 环境
3. **`docker-compose.yml`** — Docker Compose 编排配置  
   - 定义 GPU / CPU 服务  
   - 卷挂载（持久化数据）  
   - 环境变量管理  
   - 健康检查支持
4. **`.dockerignore`** — 构建忽略文件  
   - 排除 `.git`, `__pycache__`, `node_modules` 等  
   - 加速构建，减小镜像体积

#### 启动脚本
1. **`docker-start.sh`** — Linux/Mac 快速启动脚本  
   - 自动检测 GPU 状态  
   - 一键启动/停止/重启服务  
   - 支持多种命令
2. **`docker-start.bat`** — Windows 快速启动脚本  
   - 功能与 Linux 版本一致  
   - 适配 Windows 命令行语法

---

### 最简单的方式（推荐新手）

```bash
# 1. 克隆项目
git clone https://github.com/LogicShao/AutoVoiceCollation
cd AutoVoiceCollation

# 2. 配置 API Keys
cp .env.example .env
# 编辑 .env 文件，填入你的 API Keys

# 3. 一键启动
# Linux/Mac:
./docker-start.sh start

# Windows:
docker-start.bat start

# 4. 访问 Web 前端
# 浏览器打开: http://localhost:8000
```

---

### 使用 Docker Compose

```bash
# GPU 版本（推荐）
docker compose up -d

# CPU 版本
docker compose --profile cpu-only up -d

# 查看日志（实时）
docker compose logs -f

# 停止服务
docker compose down
```

---

### 启动脚本命令

#### Linux/Mac (`docker-start.sh`)
```bash
./docker-start.sh start           # 自动检测并启动
./docker-start.sh start-gpu       # 强制使用 GPU
./docker-start.sh start-cpu       # 使用 CPU 模式
./docker-start.sh stop            # 停止服务
./docker-start.sh restart         # 重启服务
./docker-start.sh logs            # 查看日志
./docker-start.sh build           # 重新构建镜像
./docker-start.sh clean           # 清理容器和镜像
./docker-start.sh help            # 显示帮助
```

#### Windows (`docker-start.bat`)
```cmd
docker-start.bat start            # 启动 GPU 模式
docker-start.bat start-cpu        # 启动 CPU 模式
docker-start.bat stop             # 停止服务
docker-start.bat restart          # 重启服务
docker-start.bat logs             # 查看日志
docker-start.bat build            # 重新构建镜像
docker-start.bat clean            # 清理容器和镜像
docker-start.bat help             # 显示帮助
```

---

## ⚠️ 前置要求

| 组件 | 要求 |
|------|------|
| **Docker** | 20.10+ |
| **Docker Compose** | 2.0+ |
| **NVIDIA Docker**（GPU 加速） | 可选，用于 GPU 加速 |

### 安装 Docker

#### 🔹 Linux (Ubuntu/Debian)
```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose 插件
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 将当前用户加入 docker 组
sudo usermod -aG docker $USER
newgrp docker
```

#### 🔹 Windows/macOS
- 下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)

---

### 安装 NVIDIA Docker（GPU 加速，可选）

如果你有 NVIDIA GPU 并希望启用 GPU 加速：

```bash
# 安装 NVIDIA Container Toolkit
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
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

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑配置文件，填入你的 API Keys
nano .env  # 或使用 vim/vscode
```

#### ✅ 最小配置示例（`.env`）
```env
# 至少配置一个 API Key（根据你要使用的 LLM 服务）
DEEPSEEK_API_KEY=sk-your-key-here
# 或
GEMINI_API_KEY=your-gemini-key-here
# 或
DASHSCOPE_API_KEY=your-dashscope-key-here
# 或
CEREBRAS_API_KEY=your-cerebras-key-here

# 基本路径配置
OUTPUT_DIR=./out
DOWNLOAD_DIR=./download
TEMP_DIR=./temp
LOG_DIR=./logs
MODEL_DIR=./models

# ASR 模型
ASR_MODEL=paraformer

# LLM 服务（根据 API Key 选择）
LLM_SERVER=Cerebras:Qwen-3-235B-Instruct

# 设备配置（Docker 中自动检测）
DEVICE=auto
```

---

### 2. 构建并启动服务

#### 方式 A: 使用 GPU（推荐，性能更好）
```bash
# 构建镜像
docker compose build

# 启动服务
docker compose up -d

# 实时查看日志
docker compose logs -f
```

#### 方式 B: 仅使用 CPU
```bash
# 启动 CPU 版本
docker compose --profile cpu-only up -d

# 查看日志
docker compose logs -f autovoicecollation-api-cpu
```

#### 方式 C: 一键构建并启动
```bash
# GPU 版本
docker compose up -d --build

# CPU 版本
docker compose --profile cpu-only up -d --build
```

---

### 3. 访问 Web 前端

启动成功后，在浏览器中访问：

- **GPU 版本**：[http://localhost:8000](http://localhost:8000)
- **CPU 版本**：[http://localhost:8001](http://localhost:8001)

---

## ⚙️ 配置说明

### 环境变量（`.env`）

| 配置项 | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `GEMINI_API_KEY` | Google Gemini API Key |
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API Key |
| `CEREBRAS_API_KEY` | Cerebras API Key |
| `LLM_SERVER` | LLM 服务名称（如 `Cerebras:Qwen-3-235B-Instruct`） |
| `ASR_MODEL` | ASR 模型（`paraformer` 或 `sense_voice`） |
| `USE_ONNX` | 启用 ONNX Runtime 加速（`true`） |

---

### 端口配置

默认端口：
- GPU 版本：`8000`
- CPU 版本：`8001`

修改方法：编辑 `docker-compose.yml`
```yaml
ports:
  - "8080:8000"  # 将 Web 前端 映射到主机 8080 端口
```

---

### 卷挂载（持久化数据）

自动创建并挂载以下目录：
- `./out` — 输出文件（PDF/ZIP）
- `./download` — 下载的视频/音频
- `./temp` — 临时文件
- `./logs` — 日志文件
- `./models` — 模型缓存

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

# 实时查看日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f autovoicecollation-api

# 进入容器调试
docker compose exec autovoicecollation-api bash
```

### 镜像管理
```bash
# 重新构建（代码更新后）
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
```yaml
ports:
  - "8080:8000"  # 映射到主机 8080 端口
```

### 使用自定义模型目录
```yaml
volumes:
  - /path/to/your/models:/app/models  # 挂载本地模型
```

### 限制 GPU 使用
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          device_ids: ['0']  # 仅使用 GPU 0
          capabilities: [gpu]
```

### 内存限制
```yaml
deploy:
  resources:
    limits:
      memory: 16G  # 最大 16GB
    reservations:
      memory: 8G   # 预留 8GB
```

---

## 🔧 故障排除

### 0. 网络连接问题（最常见）⭐

#### ❌ 错误信息：
```text
Connection failed [IP: 91.189.91.81 80]
500 reading HTTP response body: unexpected EOF
E: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/jammy-backports/InRelease
```

#### ✅ 解决方案：
✅ **已集成阿里云镜像源**，直接重建即可：

```bash
# 清理构建缓存
docker builder prune -f

# 重新构建
docker compose build --no-cache

# 或使用启动脚本
./docker-start.sh build
./docker-start.sh start
```

> 📌 详细解决方案请参考：[DOCKER_NETWORK_TROUBLESHOOTING.md](DOCKER_NETWORK_TROUBLESHOOTING.md)  
> 包含：镜像源切换、代理配置、Docker 加速器设置

---

### 1. 端口已被占用

#### ❌ 错误信息：
```text
Error: bind: address already in use
```

#### ✅ 解决方案：
```bash
# 查看占用进程
sudo lsof -i :8000

# 修改 `docker-compose.yml` 中的端口
ports:
  - "8001:8000"
```

---

### 2. GPU 不可用

#### ❌ 错误信息：
```text
Could not find GPU device
```

#### ✅ 解决方案：
```bash
# 1. 验证 NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# 2. 若失败，重新安装
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 3. 或使用 CPU 版本
docker compose --profile cpu-only up -d
```

---

### 3. 模型下载慢或失败

#### ✅ 解决方案：
1. 手动下载模型至 `./models/` 目录
2. 在 `.env` 中设置 `MODEL_DIR=./models`
3. 挂载预下载模型：
```yaml
volumes:
  - ./models:/app/models
```

---

### 4. 权限问题

#### ❌ 错误信息：
```text
Permission denied: '/app/out'
```

#### ✅ 解决方案：
```bash
# 修改目录权限
chmod -R 777 ./out ./download ./temp ./logs ./models
```

---

### 5. 内存不足（OOM）

#### ❌ 错误信息：
```text
CUDA out of memory
```

#### ✅ 解决方案：
1. 降低批处理大小（在 `.env` 中调整）
2. 使用 CPU 版本
3. 启用 ONNX：`USE_ONNX=true`

---

### 6. 查看日志
```bash
# 实时查看
docker compose logs -f

# 查看最近 100 行
docker compose logs --tail=100

# 导出日志
docker compose logs > docker-logs.txt
```

---

## 📊 性能优化建议

### 1. 启用 ONNX Runtime
```env
USE_ONNX=true
ONNX_PROVIDERS=CUDAExecutionProvider,CPUExecutionProvider
```

在 `Dockerfile` 中取消注释：
```dockerfile
RUN pip install onnxruntime-gpu>=1.20.0
```

### 2. 模型缓存优化
```yaml
volumes:
  - ~/.cache/modelscope:/root/.cache/modelscope
  - ~/.cache/huggingface:/root/.cache/huggingface
```

### 3. 多阶段构建（减小镜像体积）
```dockerfile
# 构建阶段
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# 运行阶段
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🌐 生产环境部署建议

### 1. 使用反向代理（Nginx）
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. 使用 HTTPS
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. 配置日志轮转
创建 `/etc/logrotate.d/autovoicecollation`：
```conf
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
已在 `docker-compose.yml` 中启用：
```yaml
restart: unless-stopped
```

### 5. 监控资源
```bash
# 实时监控
docker stats autovoicecollation-api

# 导出数据
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" > stats.txt
```

---

## 🔒 安全建议

1. ❌ **不要提交 `.env` 到 Git**（已通过 `.gitignore` 保护）
2. ✅ **定期更新镜像**：`docker compose pull && docker compose up -d`
3. ✅ **使用 secrets 管理敏感信息**（生产环境）
4. ✅ **避免使用 `--privileged`**
5. ✅ **定期备份数据**

---

## 📝 更新项目

当代码更新后：
```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建
docker compose build --no-cache

# 3. 重启服务
docker compose down
docker compose up -d

# 4. 验证
docker compose ps
docker compose logs -f
```

---

## 🆘 获取帮助

遇到问题？请按顺序操作：

1. ✅ 查看日志：`docker compose logs -f`
2. ✅ 检查状态：`docker compose ps`
3. ✅ 进入容器调试：`docker compose exec autovoicecollation-api bash`
4. ✅ 提交 Issue：[GitHub Issues](https://github.com/LogicShao/AutoVoiceCollation/issues)

---

## 📚 相关资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [NVIDIA Docker 文档](https://github.com/NVIDIA/nvidia-docker)
- [AutoVoiceCollation 项目主页](https://github.com/LogicShao/AutoVoiceCollation)

---

- **最后更新**：2025-12-17  
- **文档版本**：2.0  
- **状态**：✅ 已发布，适用于新成员培训与生产部署

✅ 本文档已优化，适合用于：
- 团队协作
- CI/CD 配置
- 新成员入职
- 项目文档归档
