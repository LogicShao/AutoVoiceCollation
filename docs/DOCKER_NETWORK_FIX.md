# Docker 网络问题解决方案

## 问题描述

如果你在构建 Docker 镜像时遇到类似以下的错误：

```
Connection failed [IP: 91.189.91.81 80]
500 reading HTTP response body: unexpected EOF
E: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/jammy-backports/InRelease
```

这是因为网络连接问题，尤其在中国大陆地区访问 Ubuntu 官方源速度慢或连接失败。

## ✅ 已集成的解决方案

**好消息**：我们已经在 `Dockerfile` 和 `Dockerfile.cpu` 中集成了阿里云镜像源，你可以直接重新构建：

```bash
# 清理之前失败的构建缓存
docker builder prune -f

# 重新启动（会自动构建）
.\docker-start.bat start
```

## 📋 其他解决方案

如果阿里云镜像源仍然有问题，可以尝试以下方案：

### 方案一：使用清华大学镜像源

修改 `Dockerfile` 第 17-18 行：

```dockerfile
# 使用清华大学镜像源
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list
```

同时修改 pip 镜像源（第 34 行）：

```dockerfile
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn
```

### 方案二：使用中科大镜像源

```dockerfile
# 使用中科大镜像源
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list
```

pip 镜像源：

```dockerfile
RUN pip config set global.index-url https://mirrors.ustc.edu.cn/pypi/web/simple/ && \
    pip config set install.trusted-host mirrors.ustc.edu.cn
```

### 方案三：使用代理

如果你有可用的 HTTP 代理：

#### 方式 A: 临时使用代理构建

```bash
# Windows (PowerShell)
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
docker compose build

# Linux/Mac
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
docker compose build
```

#### 方式 B: 在 Dockerfile 中配置代理

在 `Dockerfile` 开头添加（构建完成后可以删除）：

```dockerfile
# 构建时使用代理（根据实际情况修改端口）
ARG HTTP_PROXY=http://host.docker.internal:7890
ARG HTTPS_PROXY=http://host.docker.internal:7890
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
```

然后在构建完成后，删除这些行或注释掉。

### 方案四：配置 Docker 守护进程代理

创建或编辑 `~/.docker/config.json`（Linux/Mac）或 `%USERPROFILE%\.docker\config.json`（Windows）：

```json
{
  "proxies": {
    "default": {
      "httpProxy": "http://127.0.0.1:7890",
      "httpsProxy": "http://127.0.0.1:7890",
      "noProxy": "localhost,127.0.0.1"
    }
  }
}
```

然后重启 Docker Desktop 或 Docker 服务。

### 方案五：直接使用预构建的基础镜像

如果网络问题持续，可以考虑使用国内的镜像仓库：

在 `docker-compose.yml` 中添加镜像加速器配置，或修改 Docker Desktop 的设置：

**Docker Desktop 设置**：

1. 打开 Docker Desktop
2. 进入 Settings → Docker Engine
3. 添加以下配置：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

4. 点击 "Apply & Restart"

## 🔍 调试步骤

### 1. 清理构建缓存

```bash
# 清理所有构建缓存
docker builder prune -a -f

# 清理所有未使用的资源
docker system prune -a -f
```

### 2. 查看详细构建日志

```bash
# 使用 --progress=plain 查看详细输出
docker compose build --progress=plain
```

### 3. 测试网络连接

在 Docker 容器中测试网络：

```bash
docker run --rm ubuntu:22.04 bash -c "apt-get update"
```

如果失败，说明网络配置有问题。

### 4. 检查 DNS 设置

在 Docker Desktop 的 Settings → Resources → Network 中检查 DNS 设置。

推荐的 DNS：

- `8.8.8.8` (Google DNS)
- `223.5.5.5` (阿里云 DNS)
- `114.114.114.114` (国内 DNS)

## 📊 各镜像源速度对比

| 镜像源  | 访问速度（中国大陆） | 稳定性   | 推荐度   |
|------|------------|-------|-------|
| 阿里云  | ⭐⭐⭐⭐⭐      | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 清华大学 | ⭐⭐⭐⭐⭐      | ⭐⭐⭐⭐  | ⭐⭐⭐⭐  |
| 中科大  | ⭐⭐⭐⭐       | ⭐⭐⭐⭐  | ⭐⭐⭐⭐  |
| 官方源  | ⭐          | ⭐⭐    | ⭐     |

## 🚀 推荐流程

1. **首次尝试**：使用已集成的阿里云镜像源
   ```bash
   docker builder prune -f
   .\docker-start.bat start
   ```

2. **如果仍失败**：切换到清华大学镜像源
    - 修改 `Dockerfile` 中的镜像源配置
    - 重新构建

3. **如果还是失败**：配置代理
    - 设置环境变量或修改 Docker 配置
    - 使用代理构建

4. **终极方案**：
    - 配置 Docker 镜像加速器
    - 使用本地代理或 VPN
    - 考虑使用云服务器构建镜像

## ⚠️ 注意事项

1. **不要同时使用多个方案**，可能会导致冲突
2. **修改后记得清理缓存**：`docker builder prune -f`
3. **代理配置不要提交到 Git**
4. **如果使用代理，构建完成后记得移除代理配置**

## 📝 完整的 Dockerfile 示例（阿里云镜像源）

这是已经集成在项目中的配置：

```dockerfile
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# 使用阿里云镜像源（加速国内访问）
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git wget curl build-essential libsndfile1 \
    fonts-wqy-zenhei fonts-noto-cjk \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用国内镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

# 其余配置...
```

## 🆘 仍然无法解决？

如果尝试了所有方法仍然无法解决，请：

1. 提供完整的错误日志
2. 说明你的网络环境（是否在公司网络、是否使用代理等）
3. 提交 Issue：https://github.com/LogicShao/AutoVoiceCollation/issues
4. 考虑使用云服务器（如阿里云、腾讯云）构建镜像

---

**最后更新**: 2025-11-07
