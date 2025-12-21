# 日志系统使用指南

> ✅ 项目版本：v2.0 | 日志系统基于 `structlog` + `logging` 构建，支持结构化输出与多级控制

---

## 📌 日志配置

日志配置位于 `src/config.py`，包含以下核心参数：

```python
LOG_LEVEL = 'INFO'              # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = './logs/AutoVoiceCollation.log'  # 日志文件路径
LOG_CONSOLE_OUTPUT = True       # 是否输出到控制台
LOG_COLORED_OUTPUT = True       # 控制台输出是否启用彩色
```

### 🔍 日志级别说明

| 级别 | 用途 | 适用场景 |
|------|------|----------|
| `DEBUG` | 详细调试信息 | 开发阶段，用于追踪执行流程 |
| `INFO`  | 一般运行信息 | 默认级别，记录关键流程节点 |
| `WARNING` | 潜在问题提示 | 非致命异常，如 API 限流警告 |
| `ERROR` | 错误但可恢复 | 出现异常但程序仍能继续运行 |
| `CRITICAL` | 严重错误 | 可能导致服务崩溃或中断 |

---

## 🛠️ 使用方法

### 1. 在模块中导入 logger

```python
from src.logger import get_logger

logger = get_logger(__name__)
```

> 💡 `__name__` 会自动注入模块名，便于定位日志来源。

### 2. 使用不同级别的日志

```python
# DEBUG - 调试信息
logger.debug(f"处理的数据: {data}")

# INFO - 一般信息
logger.info("开始处理音频文件")
logger.info(f"文件路径: {file_path}")

# WARNING - 警告
logger.warning("API 调用接近速率限制")
logger.warning(f"重试次数: {retry_count}/{max_retries}")

# ERROR - 错误
logger.error(f"文件读取失败: {error_message}")

# CRITICAL - 严重错误
logger.critical("数据库连接失败，程序即将退出")
```

---

## 🖨️ 日志输出格式

### ✅ 控制台输出（带颜色）

```text
2025-10-21 14:30:45 - src.extract_audio_text - INFO - Loading Paraformer model...
2025-10-21 14:30:50 - src.extract_audio_text - INFO - Paraformer model loaded successfully.
2025-10-21 14:31:00 - src.bilibili_downloader - WARNING - 下载失败（第 1 次），错误信息：网络超时
```

> 🎨 彩色输出区分级别：  
> - `DEBUG`：蓝色  
> - `INFO`：绿色  
> - `WARNING`：黄色  
> - `ERROR`：红色  
> - `CRITICAL`：亮红色

### 📁 文件输出

- **路径**：`./logs/AutoVoiceCollation.log`
- **格式**：纯文本，无颜色代码
- **行为**：追加写入，不会覆盖旧日志

---

## 🔍 调试技巧

### 1. 开发时启用 `DEBUG` 级别

修改 `src/config.py`：
```python
LOG_LEVEL = 'DEBUG'  # 显示所有调试信息
```

### 2. 生产环境使用 `INFO` 级别

```python
LOG_LEVEL = 'INFO'  # 仅记录重要状态
```

### 3. 禁用控制台输出（仅保留文件）

```python
LOG_CONSOLE_OUTPUT = False
```

### 4. 禁用文件输出（仅控制台）

```python
LOG_FILE = None
```

---

## 🔄 迁移指南（从 `print` 到 `logger`）

### ❌ 旧代码（不推荐）
```python
print(f"开始处理文件：{filename}")
print(f"错误：{error}")
```

### ✅ 新代码（推荐）
```python
from src.logger import get_logger
logger = get_logger(__name__)

logger.info(f"开始处理文件：{filename}")
logger.error(f"错误：{error}")
```

> ✅ 建议：将所有 `print` 替换为 `logger`，提高可维护性和可监控性。

---

## 🗂️ 日志文件管理

- **默认路径**：`./logs/AutoVoiceCollation.log`
- **写入方式**：追加模式（`a+`），不会覆盖历史日志
- **建议操作**：
  - 定期清理旧日志（如每月归档一次）
  - 或未来集成日志轮转（`RotatingFileHandler`）

---

## 🏆 最佳实践

### 1. ✅ 使用合适的日志级别

| 场景 | 推荐级别 |
|------|----------|
| 调试变量值 | `DEBUG` |
| 启动/结束任务 | `INFO` |
| API 请求/响应 | `INFO` |
| 重试机制 | `WARNING` |
| 文件缺失/权限错误 | `ERROR` |
| 数据库断连 | `CRITICAL` |

### 2. ✅ 提供上下文信息

```python
# ✅ 好示例
logger.info(f"开始下载视频，URL: {url}, 格式: {format}")

# ❌ 差示例
logger.info("开始下载")
```

### 3. ✅ 在异常处理中使用日志

```python
try:
    process_file(filepath)
except FileNotFoundError as e:
    logger.error(f"文件不存在: {filepath}, 错误: {e}")
except Exception as e:
    logger.critical(f"未预期的错误: {e}", exc_info=True)
```

> ⚠️ `exc_info=True` 可记录完整堆栈信息，便于排查。

### 4. ✅ 记录关键操作的开始与结束

```python
logger.info(f"开始处理任务: {task_id}")
# ... 处理逻辑 ...
logger.info(f"任务完成: {task_id}, 耗时: {elapsed_time:.2f}秒")
```

### 5. ✅ 避免记录敏感信息

```python
# ❌ 危险：暴露 API Key
logger.debug(f"API请求参数: {api_params}")

# ✅ 安全：过滤敏感字段
safe_params = {k: v for k, v in api_params.items() if k not in ['api_key', 'password']}
logger.debug(f"API请求参数: {safe_params}")
```

---

## ❓ 常见问题解答

### Q1: 为什么看不到 `DEBUG` 日志？

> A: 检查 `LOG_LEVEL` 是否设置为 `'DEBUG'`。当前级别为 `INFO` 时，`DEBUG` 日志会被忽略。

### Q2: 如何关闭彩色输出？

> A: 设置 `LOG_COLORED_OUTPUT = False`，控制台将显示纯色文本。

### Q3: 日志文件太大怎么办？

> A: 当前为追加模式，建议：
> - 手动清理旧日志
> - 未来可集成 `RotatingFileHandler` 实现日志轮转（按大小或时间切割）

### Q4: 能否为不同模块设置不同日志级别？

> A: 当前全局统一配置。若需细粒度控制，可在 `logger.py` 中扩展 `LoggerAdapter` 或按模块配置。

### Q5: 如何在日志中包含完整的异常堆栈？

> A: 使用 `exc_info=True` 参数：
```python
try:
    risky_operation()
except Exception as e:
    logger.error(f"操作失败: {e}", exc_info=True)
```

---

## 📚 相关文档

- [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) —— 项目开发规范
- [CLAUDE.md](CLAUDE.md) —— 项目设计与架构建议
- [LOGGING.md](docs/LOGGING.md) —— 本文件（当前）

---

- **最后更新**：2025-12-17  
- **文档版本**：2.0  
- **状态**：✅ 已发布，适用于团队协作与新成员培训

✅ 本文档已优化，适合用于：
- 团队内部培训
- CI/CD 配置
- 日志审计与故障排查
