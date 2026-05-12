# WSL2 + Windows Conda 环境 MCP 配置避坑指南

> 适用场景：在 WSL2 中运行 Hermes Agent（或其他 MCP Client），
> 并通过 stdio transport 调用 Windows 端的 Conda Python MCP Server。

---

## 背景

WSL2 可以通过 `/mnt/<drive>/...` 直接调用 Windows 可执行文件（binfmt_misc 互操作），
但这个过程存在多个隐蔽的环境变量传递与编码兼容问题。

---

## 坑 1：WSL interop 过滤环境变量

### 现象

`PYTHONPATH` 等自定义环境变量在 WSL 启动 Windows 进程时被**静默丢弃**。
即使 `config.yaml` 中正确配置了：

```yaml
env:
  PYTHONPATH: E:\proj\AutoVoiceCollation
```

Windows Python 进程中 `os.environ['PYTHONPATH']` 仍为 `NOT SET`。

### 原因

WSL2 的 Windows 进程互操作层只会传递少量系统级环境变量
（`PATH`、`SYSTEMROOT`、`WINDIR` 等），其余变量一律过滤。

### 修复：使用 `.pth` 文件注入 `sys.path`

在 Windows Conda 环境的 `site-packages` 下创建 `.pth` 文件：

```powershell
# 在 Windows 端执行：
echo E:\proj\AutoVoiceCollation > D:\conda_envs\autovoicecollation\Lib\site-packages\autovoicecollation.pth
```

或从 WSL 端：

```bash
echo 'E:\proj\AutoVoiceCollation' > /mnt/d/conda_envs/autovoicecollation/Lib/site-packages/autovoicecollation.pth
```

验证：

```bash
/mnt/d/conda_envs/autovoicecollation/python.exe -c "import sys; print([p for p in sys.path if 'AutoVoice' in p])"
# 应输出: ['E:\\proj\\AutoVoiceCollation']
```

> `.pth` 文件是 Python 启动时自动处理的路径配置文件，不依赖环境变量，WSL interop 无法过滤。

---

## 坑 2：Windows 默认编码 GBK 导致 Emoji Crash

### 现象

MCP Server 启动时报错：

```
UnicodeEncodeError: 'gbk' codec can't encode character '\u26a0' in position 0
```

### 原因

中文 Windows 的 console 默认编码为 GBK，无法编码 emoji 字符（如 `⚠️`）。
当项目代码中有 `print("⚠️ 警告...")` 时，在 MCP stdio 上下文中会崩溃。

而 WSL 终端是 UTF-8，直接在 bash 中测试往往不触发此问题。

### 修复：启用 Python UTF-8 模式

在 MCP 配置的 `args` 中添加 `-X utf8`：

```yaml
mcp_servers:
  avc:
    command: /mnt/d/conda_envs/autovoicecollation/python.exe
    args:
      - -X
      - utf8       # ← 启用 PEP 540 UTF-8 模式
      - -m
      - src.mcp.server
```

`-X utf8` 必须在 `-m` 之前。

---

## 坑 3：Logger 往 stdout 写，污染 JSONRPC 协议流

### 现象

Hermes 日志中出现：

```
ERROR mcp.client.stdio: Failed to parse JSONRPC message from server
```

同时 MCP stderr 日志可见 logger 输出混入了协议通道。

### 原因

MCP stdio transport 使用 **stdout 承载 JSONRPC 协议**，stderr 用于日志。
但项目 logger 默认 `StreamHandler(sys.stdout)`，所有日志输出直接写入 stdout，
导致 MCP Client 收到非法 JSON。

此外，MCP transport 关闭后，logger 往已关闭的 stream 写入会抛出 `ValueError`。

### 修复：重定向 Logger 到 stderr + 容错

在 MCP Server 入口（`src/mcp/server.py`）模块加载时执行：

```python
import logging
import sys

def _fix_mcp_logging():
    """Reconfigure logger for MCP stdio transport."""
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
            handler.stream = sys.stderr

    # 防止 stdio 关闭后 logger 写失败导致 crash
    logging.raiseExceptions = False

_fix_mcp_logging()
```

---

## 完整 MCP 配置参考（Hermes Agent ~/.hermes/config.yaml）

```yaml
mcp_servers:
  avc:
    command: /mnt/d/conda_envs/autovoicecollation/python.exe
    cwd: /mnt/e/proj/AutoVoiceCollation
    args:
      - -X
      - utf8
      - -m
      - src.mcp.server
    enabled: true
    env:
      PYTHONPATH: E:\proj\AutoVoiceCollation   # 留作参考，实际靠 .pth 文件
```

> 别忘了在 Windows Conda 环境中部署 `autovoicecollation.pth` 文件（见坑1）。

---

## Q&A

### Q: 为什么不用 WSL 内的 Python 环境？

可以，但本项目的依赖（`funasr`、`modelscope`、Windows 版 `onnxruntime` 等）
在 Linux/WSL 下可能有兼容性问题。使用 Windows Conda 环境保持与 Windows 原生运行一致。

### Q: `-X utf8` 会影响 Linux 端运行吗？

不会。`-X utf8` 在 Linux（默认 UTF-8 locale）下是空操作，只在 Windows 端生效。

### Q: 如何验证 MCP 连接成功？

```bash
# 查看 Hermes 日志
grep "MCP:" ~/.hermes/logs/agent.log | tail -3

# 成功示例：
# MCP: registered 7 tool(s) from 1 server(s) (0 failed)

# 失败示例：
# MCP: 0 tool(s) from 0 server(s) (1 failed)
```

### Q: `.pth` 文件会影响非 MCP 场景吗？

`.pth` 文件会在**该 Conda 环境下所有 Python 进程**启动时生效，
将项目路径加入 `sys.path`。这是预期行为，不影响其他项目（路径唯一）。
如需移除，删除该 `.pth` 文件即可。
