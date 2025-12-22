
# Docker 容器崩溃问题诊断和解决方案

## 问题症状

- CPU 占用 99.79%
- 浏览器访问时出现 ERR_CONNECTION_RESET
- Docker 容器崩溃

## 原因分析

### 最可能的原因：模型加载导致资源耗尽

#### FunASR 模型首次加载时：

1. 自动从网络下载模型（1-3GB）
2. 解压和加载到内存
3. 导致 CPU 100% 和内存占用激增
4. 如果内存不足，容器被系统 OOM Killer 杀死

## 解决方案

### 方案一：重新启动并等待模型加载完成（推荐）

我已经更新了 `docker-compose.yml`，增加了：

- 内存限制：8GB（可根据实际调整）
- 健康检查等待时间：从 60 秒增加到 180 秒
- 重试次数：从 3 次增加到 10 次

#### 操作步骤
```bash
# 1. 停止当前容器
docker compose down

# 2. 重新启动
docker compose up -d

# 3. 实时查看日志，等待模型加载完成
docker compose logs -f

# 期望看到的正常日志：
# - "Loading model..."
# - "Model loaded successfully"
# - "Running on http://0.0.0.0:7860"
```

#### 等待时间
首次启动可能需要 **3-5 分钟**，取决于：

- 网络速度（下载模型）
- CPU/内存性能（加载模型）

### 方案二：预先下载模型（避免启动时下载）

#### 优点
避免容器启动时下载模型导致的资源峰值

```bash
# 1. 停止容器
docker compose down

# 2. 创建模型目录
mkdir -p ./models

# 3. 在容器外预先下载模型（需要 Python 环境）
python -c "
from funasr import AutoModel
# 下载 Paraformer 模型
AutoModel(model='paraformer-zh', model_revision='v2.0.4', cache_dir='./models')
# 下载 SenseVoice 模型（如果使用）
AutoModel(model='SenseVoiceSmall', cache_dir='./models')
"

# 4. 重新启动容器（会使用本地模型）
docker compose up -d
```

### 方案三：降低资源需求（使用轻量级配置）

修改 `.env` 文件，使用更轻量的配置：

```env
# 使用 SenseVoice 模型（比 Paraformer 更轻量）
ASR_MODEL=sense_voice

# 启用 ONNX 加速（降低内存占用）
USE_ONNX=true

# 禁用 LLM 润色（如果不需要）
DISABLE_LLM_POLISH=true
DISABLE_LLM_SUMMARY=true
```

然后重启容器：

```bash
docker compose down
docker compose up -d
```

### 方案四：增加系统资源

#### 如果你的机器内存不足：

##### Docker Desktop 设置（Windows/Mac）

1. 打开 Docker Desktop
2. Settings → Resources
3. 增加分配给 Docker 的内存：
  - 推荐：至少 8GB
  - 如果使用 GPU 版本：推荐 12-16GB
4. Apply & Restart

##### Linux 系统
检查可用内存：
```bash
free -h
```

如果物理内存不足，考虑：

- 关闭其他应用释放内存
- 使用 CPU 版本（更轻量）
- 使用云服务器

### 方案五：使用 CPU 版本（更稳定）

如果没有 GPU 或资源受限，使用 CPU 版本：

```bash
# 停止 GPU 版本
docker compose down

# 启动 CPU 版本
docker compose --profile cpu-only up -d

# 查看日志
docker compose logs -f autovoicecollation-webui-cpu
```

#### 访问地址：http://localhost:7861

## 诊断命令

### 1. 查看容器日志
```bash
# 查看最后 100 行日志
docker compose logs --tail=100

# 实时查看日志
docker compose logs -f

# 查看崩溃前的日志（容器已停止）
docker logs avc-webui
```

### 2. 查看资源使用
```bash
# 实时监控资源
docker stats

# 查看容器状态
docker ps -a
```

### 3. 检查容器退出原因
```bash
# 查看退出代码
docker inspect avc-webui | grep -A 5 "State"

# 常见退出代码：
# 137 = 内存不足被 OOM Killer 杀死
# 1   = 程序错误退出
```

## 常见错误信息和解决方法

### 错误 1: "Killed"

#### 原因
内存不足，被系统杀死

#### 解决

- 增加 Docker 分配的内存（方案四）
- 使用轻量级配置（方案三）
- 预先下载模型（方案二）

### 错误 2: "CUDA out of memory"

#### 原因
GPU 显存不足

#### 解决

- 使用 CPU 版本（方案五）
- 或在 `.env` 中设置 `DEVICE=cpu`

### 错误 3: "Connection refused" 或 "Connection reset"

#### 原因
容器还在启动中，模型未加载完成

#### 解决

- 等待 3-5 分钟
- 查看日志确认启动状态：`docker compose logs -f`

### 错误 4: "Model download failed"

#### 原因
网络问题无法下载模型

#### 解决

- 使用代理或 VPN
- 或手动下载模型（方案二）
- 检查网络连接

## 验证修复

启动成功后，你应该能够：

1. **查看容器状态**：
```bash
docker ps
# 看到 avc-webui 状态为 Up
```

2. **访问 WebUI**：
  - 打开浏览器访问 http://localhost:7860
  - 应该看到 Gradio 界面

3. **查看日志**：
```bash
docker compose logs --tail=20
# 看到 "Running on http://0.0.0.0:7860"
```

## 预防措施

为了避免将来再次出现问题：

1. **始终预留足够内存**：Docker 分配至少 8GB
2. **首次启动耐心等待**：模型加载需要时间
3. **定期查看日志**：`docker compose logs -f`
4. **监控资源使用**：`docker stats`
5. **保留模型缓存**：不要删除 `./models` 目录

---

- **更新时间**: 2025-11-07
- **适用版本**: Docker Compose V2+
