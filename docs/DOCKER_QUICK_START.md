# Docker 部署快速参考

## 📦 已创建的文件

本次为 AutoVoiceCollation 项目创建了完整的 Docker 部署方案，包含以下文件：

### 核心文件

1. **Dockerfile** - GPU 版本的 Docker 镜像配置
    - 基于 PyTorch CUDA 镜像
    - 包含 FFmpeg 和必要的系统依赖
    - 支持 GPU 加速

2. **Dockerfile.cpu** - CPU 版本的 Docker 镜像配置
    - 基于 Python 3.11 镜像
    - 适合没有 GPU 的环境

3. **docker-compose.yml** - Docker Compose 编排配置
    - GPU 和 CPU 版本的服务定义
    - 卷挂载配置（持久化数据）
    - 环境变量配置
    - 健康检查

4. **.dockerignore** - Docker 构建忽略文件
    - 排除不必要的文件以加速构建
    - 减小镜像体积

### 启动脚本

5. **docker-start.sh** - Linux/Mac 快速启动脚本
    - 自动检测 GPU
    - 依赖检查
    - 一键启动/停止服务
    - 支持多种命令

6. **docker-start.bat** - Windows 快速启动脚本
    - 与 Linux 版本功能相同
    - 适配 Windows 命令行

### 文档

7. **DOCKER.md** - 完整的 Docker 部署文档
    - 详细的安装步骤
    - 配置说明
    - 故障排除
    - 性能优化建议
    - 生产环境部署指南

8. **README.md** - 更新了主文档
    - 添加了 Docker 部署章节
    - 更新了常见问题

## 🚀 快速开始

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

# 4. 访问 WebUI
# 浏览器打开: http://localhost:7860
```

### 使用 Docker Compose

```bash
# GPU 版本
docker compose up -d

# CPU 版本
docker compose --profile cpu-only up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

## 📋 启动脚本命令

### Linux/Mac (docker-start.sh)

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

### Windows (docker-start.bat)

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

## ⚙️ 配置说明

### 环境变量配置 (.env)

最小配置示例：

```env
# API Keys（至少配置一个）
DEEPSEEK_API_KEY=sk-your-key-here
# 或
GEMINI_API_KEY=your-gemini-key-here
# 或
DASHSCOPE_API_KEY=your-dashscope-key-here

# 基本配置
OUTPUT_DIR=./out
DOWNLOAD_DIR=./download
TEMP_DIR=./temp
LOG_DIR=./logs
MODEL_DIR=./models

# ASR 模型
ASR_MODEL=paraformer

# LLM 服务
LLM_SERVER=Cerebras:Qwen-3-235B-Instruct

# 设备配置
DEVICE=auto  # Docker 中自动检测
```

### 端口配置

默认端口：

- **GPU 版本**: 7860
- **CPU 版本**: 7861

修改端口：编辑 `docker-compose.yml`

```yaml
ports:
  - "8080:7860"  # 将 WebUI 映射到 8080 端口
```

### 卷挂载

默认挂载的目录（自动创建）：

- `./out` - 输出文件
- `./download` - 下载的视频/音频
- `./temp` - 临时文件
- `./logs` - 日志文件
- `./models` - 模型缓存

## 🔧 常见问题

### 1. 端口被占用

```bash
# 修改 docker-compose.yml 中的端口
ports:
  - "7861:7860"  # 使用其他端口
```

### 2. GPU 不可用

```bash
# 验证 NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# 如果失败，使用 CPU 版本
./docker-start.sh start-cpu
```

### 3. 查看日志

```bash
# 实时查看
docker compose logs -f

# 查看最近 100 行
docker compose logs --tail=100

# 导出到文件
docker compose logs > logs.txt
```

### 4. 进入容器调试

```bash
docker compose exec autovoicecollation-webui bash
```

### 5. 重新构建镜像

```bash
# 清理缓存后重建
docker compose build --no-cache

# 或使用启动脚本
./docker-start.sh build
```

## 📊 性能建议

### GPU 环境

- 推荐使用 GPU 版本，性能提升显著
- 确保安装了 NVIDIA Docker Runtime
- 使用 `paraformer` 模型获得最佳准确度

### CPU 环境

- 使用 `sense_voice` 模型，速度更快
- 启用 ONNX Runtime 加速：`USE_ONNX=true`
- 考虑使用更小的 LLM 模型

### 内存优化

- 限制 Docker 内存使用（在 `docker-compose.yml` 中）
- 降低 ASR 批处理大小
- 禁用不需要的功能（润色/摘要）

## 📚 详细文档

- **完整部署指南**: [DOCKER.md](DOCKER.md)
- **技术架构文档**: [CLAUDE.md](../CLAUDE.md)
- **主项目文档**: [README.md](../README.md)

## 🆘 获取帮助

如果遇到问题：

1. 查看日志：`docker compose logs -f`
2. 阅读完整文档：[DOCKER.md](DOCKER.md)
3. 提交 Issue：https://github.com/LogicShao/AutoVoiceCollation/issues

## 🎯 下一步

启动成功后，你可以：

1. **使用 WebUI**: http://localhost:7860
    - 上传音频/视频文件
    - 输入 B站链接
    - 配置 LLM 参数
    - 生成字幕

2. **使用 API**: http://localhost:8000/docs
    - RESTful API 接口
    - 支持批量处理
    - 任务状态查询

3. **查看输出**:
    - PDF 文档：`./out/`
    - 下载文件：`./download/`
    - 日志文件：`./logs/`

## 📝 更新说明

更新项目代码后：

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建并启动
./docker-start.sh build
./docker-start.sh start
```

---

**Happy Coding! 🚀**

如有问题，欢迎提 Issue 或 PR！
