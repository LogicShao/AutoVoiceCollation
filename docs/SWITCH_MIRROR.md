# Docker 镜像源切换指南

## 🔍 问题诊断

如果你看到 `502 Bad Gateway` 错误，说明当前使用的镜像源不可用。

当前 Dockerfile 使用：**清华大学镜像源**

## 📊 快速测试镜像源

运行测试脚本找到最快的镜像源：

```bash
# Windows
.\test-mirrors.bat

# Linux/Mac
./test-mirrors.sh
```

## 🔄 切换镜像源

### 方案一：修改 Dockerfile（推荐）

编辑 `Dockerfile` 第 21-22 行，替换为你测试后最快的镜像源：

#### 选项 1：清华大学（当前使用）

```dockerfile
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list
```

#### 选项 2：阿里云

```dockerfile
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list
```

#### 选项 3：中科大

```dockerfile
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list
```

#### 选项 4：网易

```dockerfile
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.163.com@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.163.com@g' /etc/apt/sources.list
```

#### 选项 5：华为云

```dockerfile
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.huaweicloud.com@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.huaweicloud.com@g' /etc/apt/sources.list
```

### 方案二：使用代理构建

如果你有可用的代理（如 Clash、V2Ray 等）：

#### 方式 A：环境变量（临时）

```bash
# Windows (PowerShell)
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
docker compose build

# Windows (CMD)
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
docker compose build

# Linux/Mac
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
docker compose build
```

#### 方式 B：使用代理 Dockerfile

```bash
# 使用 Dockerfile.proxy 构建
docker compose -f docker-compose.proxy.yml build --build-arg HTTP_PROXY=http://127.0.0.1:7890 --build-arg HTTPS_PROXY=http://127.0.0.1:7890
```

或创建 `docker-compose.proxy.yml`：

```yaml
services:
  autovoicecollation-webui:
    build:
      context: .
      dockerfile: Dockerfile.proxy
      args:
        HTTP_PROXY: http://127.0.0.1:7890
        HTTPS_PROXY: http://127.0.0.1:7890
    # 其他配置同 docker-compose.yml
```

### 方案三：配置 Docker Desktop 代理

**永久配置（推荐）**：

1. 打开 Docker Desktop
2. Settings → Resources → Proxies
3. 启用 "Manual proxy configuration"
4. 填入代理地址：
    - Web Server (HTTP): `http://127.0.0.1:7890`
    - Secure Web Server (HTTPS): `http://127.0.0.1:7890`
5. Apply & Restart

## 🚀 重新构建流程

选择镜像源或配置代理后：

```bash
# 1. 清理缓存
docker builder prune -f

# 2. 重新构建
docker compose build --no-cache

# 3. 启动服务
.\docker-start.bat start
```

## 📝 常见代理端口

| 代理工具  | 默认 HTTP 端口 |
|-------|------------|
| Clash | 7890       |
| V2Ray | 10809      |
| SSR   | 1080       |
| 其他    | 查看你的代理工具设置 |

**注意**：将 `127.0.0.1` 替换为你的代理地址，端口号根据实际情况修改。

## ⚠️ 注意事项

1. **不要同时修改镜像源和使用代理**，选择一种方式即可
2. **代理配置不要提交到 Git**
3. **构建成功后记得清除代理环境变量**
4. **如果使用 Dockerfile.proxy，构建完成后可以切回普通 Dockerfile**

## 🆘 仍然失败？

1. **检查网络连接**：`ping mirrors.tuna.tsinghua.edu.cn`
2. **检查代理是否运行**：访问 http://127.0.0.1:7890 （替换为你的代理端口）
3. **尝试其他镜像源**：运行 `test-mirrors.bat` 测试所有源
4. **查看详细错误**：`docker compose build --progress=plain`
5. **考虑使用云服务器**：如阿里云、腾讯云等，网络环境更稳定

## 📚 相关文档

- [完整网络问题解决方案](DOCKER_NETWORK_FIX.md)
- [Docker 部署指南](DOCKER.md)
