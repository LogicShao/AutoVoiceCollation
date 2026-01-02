
# Docker 网络问题完整解决方案

## 📋 问题概述

在 Docker 部署过程中可能遇到多种网络问题，包括：

1. **构建时网络问题**：无法下载 Ubuntu 软件包
2. **运行时网络问题**：容器无法访问外网
3. **主机访问问题**：Windows 主机无法访问容器服务
4. **镜像源问题**：国内访问国外镜像源速度慢

## 🔍 快速诊断

运行诊断脚本确定问题类型：

```bash
# Windows
.\diagnose-network.bat

# Linux/Mac
./diagnose-network.sh
```

## 🚀 通用解决方案

### 方案一：使用国内镜像源（推荐）

#### 修改 Dockerfile 镜像源

编辑 `Dockerfile` 第 21-22 行，选择最快的镜像源：

- **选项 1：阿里云（默认已集成）**

```dockerfile
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list
```

- **选项 2：清华大学**

```dockerfile
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list
```

- **选项 3：中科大**

```dockerfile
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list
```

#### 测试镜像源速度

```bash
# Windows
.\test-mirrors.bat

# Linux/Mac
./test-mirrors.sh
```

### 方案二：配置代理

如果你有可用的 HTTP 代理：

#### 临时使用代理构建

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

#### 常见代理端口

| 代理工具  | 默认 HTTP 端口 |
|-------|------------|
| Clash | 7890       |
| V2Ray | 10809      |
| SSR   | 1080       |

### 方案三：配置 Docker Desktop 代理（永久）

1. 打开 Docker Desktop
2. Settings → Resources → Proxies
3. 启用 "Manual proxy configuration"
4. 填入代理地址：
  - Web Server (HTTP): `http://127.0.0.1:7890`
  - Secure Web Server (HTTPS): `http://127.0.0.1:7890`
5. Apply & Restart

## 🪟 Windows 特定问题

### 问题：容器运行但主机无法访问

**症状**：

- 容器内服务正常运行
- 从容器内部可以访问 http://localhost:8000
- 从 Windows 主机无法访问
- 浏览器显示 ERR_CONNECTION_REFUSED

#### 解决方案

- **方案 1：重启 Docker Desktop（成功率 90%）**

1. 打开 Docker Desktop
2. 点击右上角 **设置图标（⚙️）**
3. 选择 **Restart**
4. 等待重启完成（约 1-2 分钟）
5. 重新启动容器

- **方案 2：添加 Windows 防火墙规则**  
以 **管理员身份** 运行 PowerShell 或 CMD：

```cmd
netsh advfirewall firewall add rule name="Docker Port 8000" dir=in action=allow protocol=TCP localport=8000
```

- **方案 3：检查 WSL 集成（如果使用 WSL 2）**

1. 打开 Docker Desktop
2. **Settings** → **Resources** → **WSL Integration**
3. 确保启用了 WSL 集成
4. 勾选你使用的 WSL 发行版
5. 点击 **Apply & Restart**

- **方案 4：使用不同的端口**  
修改 `docker-compose.yml`：

```yaml
ports:
  - "8080:8000"  # 使用 8080 端口
```

### 快速修复命令（Windows）

以管理员身份运行：

```cmd
REM 1. 停止容器
docker compose down

REM 2. 添加防火墙规则
netsh advfirewall firewall add rule name="Docker Port 8000" dir=in action=allow protocol=TCP localport=8000

REM 3. 重启 Docker 服务
net stop com.docker.service
net start com.docker.service

REM 4. 重新启动容器
docker compose up -d

REM 5. 等待启动
timeout /t 10

REM 6. 测试访问
curl http://localhost:8000
```

## 🐧 Linux/Mac 特定问题

### 问题：权限问题

```bash
# 修改目录权限
chmod -R 777 ./out ./download ./temp ./logs ./models
```

### 问题：DNS 解析失败

检查 Docker 守护进程 DNS 配置：

```bash
# 查看当前 DNS 配置
docker info | grep -i dns

# 修改 Docker 配置
sudo nano /etc/docker/daemon.json
```

添加 DNS 配置：

```json
{
  "dns": ["8.8.8.8", "223.5.5.5", "114.114.114.114"]
}
```

重启 Docker 服务：

```bash
sudo systemctl restart docker
```

## 🔧 调试步骤

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

### 4. 检查端口占用

```bash
# Windows
netstat -ano | findstr "8000"

# Linux/Mac
lsof -i :8000
```

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
./docker-start.sh start
```

2. **如果仍失败**：切换到清华大学镜像源
  - 修改 `Dockerfile` 中的镜像源配置
  - 重新构建

3. **如果还是失败**：配置代理
  - 设置环境变量或修改 Docker 配置
  - 使用代理构建

4. **Windows 特定问题**：
  - 重启 Docker Desktop
  - 添加防火墙规则
  - 检查 WSL 集成

5. **终极方案**：
  - 配置 Docker 镜像加速器
  - 使用本地代理或 VPN
  - 考虑使用云服务器构建镜像

## ⚠️ 注意事项

1. 不要同时使用多个方案，可能会导致冲突
2. 修改后记得清理缓存：`docker builder prune -f`
3. 代理配置不要提交到 Git
4. 如果使用代理，构建完成后记得移除代理配置
5. Windows 防火墙规则添加后需要重启容器

## 🆘 仍然无法解决？

如果尝试了所有方法仍然无法解决，请：

1. 提供完整的错误日志
2. 说明你的网络环境（是否在公司网络、是否使用代理等）
3. 提交 Issue：https://github.com/LogicShao/AutoVoiceCollation/issues
4. 考虑使用云服务器（如阿里云、腾讯云）构建镜像

---

- **最后更新**: 2025-12-16
- **适用平台**: Windows 10/11, Linux, macOS
- **问题状态**: ✅ 综合解决方案
