# Windows Docker 网络问题解决方案

## 问题描述

- 容器内服务正常运行
- 从容器内部可以访问 http://localhost:7860
- 从 Windows 主机无法访问
- 浏览器显示 ERR_CONNECTION_REFUSED

## 诊断步骤

运行诊断脚本：

```cmd
.\diagnose-network.bat
```

## 解决方案

### 方案一：重启 Docker Desktop（成功率 90%）

1. 打开 Docker Desktop
2. 点击右上角**设置图标（⚙️）**
3. 选择 **Restart**
4. 等待重启完成（约 1-2 分钟）
5. 重新启动容器：
   ```cmd
   docker compose down
   docker compose up -d
   ```
6. 在浏览器访问 http://localhost:7860

### 方案二：添加 Windows 防火墙规则

以**管理员身份**运行 PowerShell 或 CMD：

```cmd
netsh advfirewall firewall add rule name="Docker Port 7860" dir=in action=allow protocol=TCP localport=7860
```

然后重启容器：

```cmd
docker compose restart
```

### 方案三：检查 WSL 集成（如果使用 WSL 2）

1. 打开 Docker Desktop
2. **Settings** → **Resources** → **WSL Integration**
3. 确保启用了 WSL 集成
4. 勾选你使用的 WSL 发行版
5. 点击 **Apply & Restart**

### 方案四：使用不同的端口

修改 `docker-compose.yml`：

```yaml
ports:
  - "8080:7860"  # 使用 8080 端口
```

然后重新创建容器：

```cmd
docker compose down
docker compose up -d
```

访问 http://localhost:8080

### 方案五：重置 Docker Desktop 网络

1. 停止所有容器：
   ```cmd
   docker compose down
   ```

2. 打开 Docker Desktop → **Troubleshoot** → **Reset to factory defaults**

3. 等待重置完成

4. 重新构建和启动：
   ```cmd
   docker compose build
   docker compose up -d
   ```

### 方案六：使用 Docker Desktop 的端口转发

1. 打开 Docker Desktop
2. 点击容器 `avc-webui`
3. 查看 **Ports** 标签页
4. 确认端口映射是否正确显示

如果没有显示端口映射：

- 说明 docker-compose.yml 配置有问题
- 尝试重新构建容器

### 方案七：检查 Hyper-V 和虚拟化

**Windows 11/10 Pro**：

1. 打开 **Windows 功能**
2. 确保以下功能已启用：
    - Windows Subsystem for Linux
    - 虚拟机平台
    - Hyper-V（如果可用）

3. 重启计算机

4. 重新启动 Docker Desktop

## 快速修复命令

以管理员身份运行：

```cmd
REM 1. 停止容器
docker compose down

REM 2. 添加防火墙规则
netsh advfirewall firewall add rule name="Docker Port 7860" dir=in action=allow protocol=TCP localport=7860

REM 3. 重启 Docker Desktop（需要在 GUI 中操作）
REM    或重启 Docker 服务（管理员权限）
net stop com.docker.service
net start com.docker.service

REM 4. 重新启动容器
docker compose up -d

REM 5. 等待启动
timeout /t 10

REM 6. 测试访问
curl http://localhost:7860
```

## 验证修复

### 测试 1：命令行测试

```cmd
curl http://localhost:7860
```

应该看到 HTML 输出（包含 "Gradio"）

### 测试 2：浏览器测试

打开浏览器访问：

- http://localhost:7860
- http://127.0.0.1:7860
- http://192.168.2.105:7860（你的本机 IP）

### 测试 3：检查端口

```cmd
netstat -ano | findstr "7860"
```

应该看到：

```
TCP    0.0.0.0:7860           0.0.0.0:0              LISTENING       [PID]
TCP    [::]:7860              [::]:0                 LISTENING       [PID]
```

## 常见错误和解决方法

### 错误 1：端口已被占用

```cmd
# 查找占用端口的进程
netstat -ano | findstr "7860"

# 终止进程（替换 [PID] 为实际进程 ID）
taskkill /F /PID [PID]
```

### 错误 2：Docker Desktop 无法启动

1. 重启计算机
2. 以管理员身份运行 Docker Desktop
3. 检查 Windows 更新
4. 重新安装 Docker Desktop

### 错误 3：WSL 2 问题

```cmd
# 更新 WSL 2 内核
wsl --update

# 重启 WSL
wsl --shutdown
```

然后重启 Docker Desktop

## 终极方案：使用 Docker Desktop 的 Port Proxy

如果以上所有方法都失败，可以手动设置端口转发：

以管理员身份运行：

```cmd
netsh interface portproxy add v4tov4 listenport=7860 listenaddress=0.0.0.0 connectport=7860 connectaddress=172.19.0.2

# 查看规则
netsh interface portproxy show all

# 删除规则（如果需要）
netsh interface portproxy delete v4tov4 listenport=7860 listenaddress=0.0.0.0
```

**注意**：将 `172.19.0.2` 替换为你的容器实际 IP（通过 `docker inspect avc-webui` 查看）

## 时区问题说明

日志中的时间不同步是正常的：

- Docker 容器默认使用 UTC 时间（协调世界时）
- 北京时间 = UTC + 8 小时

如果需要同步时区，可以在 docker-compose.yml 中添加：

```yaml
environment:
  - TZ=Asia/Shanghai
```

或挂载主机时区：

```yaml
volumes:
  - /etc/localtime:/etc/localtime:ro
```

**但这不会影响服务访问问题。**

---

**更新时间**: 2025-11-07
**适用平台**: Windows 10/11 + Docker Desktop
