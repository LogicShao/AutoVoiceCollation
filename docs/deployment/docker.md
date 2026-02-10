# Docker 部署指南（MVP）

## 1. 前置要求

- Docker 20.10+
- Docker Compose v2+
- 可选：NVIDIA 驱动 + nvidia-container-toolkit（GPU 模式）

## 2. 快速启动

在仓库根目录执行：

```bash
# 1) 准备配置
cp .env.example .env

# 2) Linux / Mac（自动检测 GPU）
bash "scripts/docker-start.sh" start

# 3) Windows
& "scripts/docker-start.bat" start
```

默认端口：

- GPU 模式：`http://localhost:8000`
- CPU 模式：`http://localhost:8001`

## 3. 常用脚本命令

### Linux / Mac

```bash
bash "scripts/docker-start.sh" start
bash "scripts/docker-start.sh" start-gpu
bash "scripts/docker-start.sh" start-cpu
bash "scripts/docker-start.sh" stop
bash "scripts/docker-start.sh" restart
bash "scripts/docker-start.sh" logs
bash "scripts/docker-start.sh" build
bash "scripts/docker-start.sh" clean
```

### Windows

```bat
& "scripts/docker-start.bat" start
& "scripts/docker-start.bat" start-cpu
& "scripts/docker-start.bat" stop
& "scripts/docker-start.bat" restart
& "scripts/docker-start.bat" logs
& "scripts/docker-start.bat" build
& "scripts/docker-start.bat" clean
```

## 4. 手动 Compose 启动（可选）

```bash
# GPU
docker compose --profile gpu up -d

# CPU
docker compose --profile cpu-only up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

## 5. 常见问题（合并版）

### 5.1 容器启动后访问失败

- 检查容器状态：`docker compose ps`
- 检查日志：`docker compose logs -f`
- 检查端口是否占用：`8000`（GPU）/`8001`（CPU）

### 5.2 首次启动慢或看起来“卡住”

- 首次会下载/加载模型，耗时可能较长。
- 建议先观察日志，不要立刻重启。

### 5.3 中文 PDF 字体乱码

- 在 `.env` 设置：`PDF_FONT_PATH` 或 `CHINESE_FONT_PATH`
- 容器内确认字体路径可访问。

### 5.4 网络拉取依赖失败

- 重试 `docker compose build --no-cache`
- 在 Docker Desktop 配置镜像加速器或代理

## 6. 数据目录说明

容器运行会挂载并持久化以下目录：

- `out/`：输出结果
- `download/`：下载与提取文件
- `temp/`：临时文件
- `logs/`：日志
- `models/`：模型缓存
