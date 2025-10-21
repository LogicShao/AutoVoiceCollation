# 日志系统使用指南

本项目使用统一的日志管理系统，替代了之前的 `print` 语句，提供更好的日志分类、格式化和管理功能。

## 日志配置

日志配置位于 `src/config.py`，包括以下参数：

```python
LOG_LEVEL = 'INFO'              # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = './logs/AutoVoiceCollation.log'  # 日志文件路径
LOG_CONSOLE_OUTPUT = True       # 是否输出到控制台
LOG_COLORED_OUTPUT = True       # 控制台输出是否使用彩色
```

### 日志级别说明

- **DEBUG**: 详细的调试信息（开发时使用）
- **INFO**: 一般信息（默认级别，记录程序运行状态）
- **WARNING**: 警告信息（潜在问题但不影响运行）
- **ERROR**: 错误信息（出现错误但程序可以继续）
- **CRITICAL**: 严重错误（可能导致程序崩溃）

## 使用方法

### 1. 在模块中导入 logger

```python
from src.logger import get_logger

logger = get_logger(__name__)
```

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

## 日志输出格式

### 控制台输出（带颜色）
```
2025-10-21 14:30:45 - src.extract_audio_text - INFO - Loading Paraformer model...
2025-10-21 14:30:50 - src.extract_audio_text - INFO - Paraformer model loaded successfully.
2025-10-21 14:31:00 - src.bilibili_downloader - WARNING - 下载失败（第 1 次），错误信息：网络超时
```

### 文件输出
日志文件保存在 `./logs/AutoVoiceCollation.log`，格式与控制台相同但不包含颜色代码。

## 调试技巧

### 1. 开发时启用 DEBUG 级别

在 `src/config.py` 中临时修改：
```python
LOG_LEVEL = 'DEBUG'  # 显示所有日志信息
```

### 2. 生产环境使用 INFO 级别

```python
LOG_LEVEL = 'INFO'  # 只显示重要信息
```

### 3. 禁用控制台输出

如果只想记录到文件：
```python
LOG_CONSOLE_OUTPUT = False
```

### 4. 禁用文件输出

如果只想在控制台查看：
```python
LOG_FILE = None
```

## 迁移指南（从 print 到 logger）

### 旧代码
```python
print(f"开始处理文件：{filename}")
print(f"错误：{error}")
```

### 新代码
```python
from src.logger import get_logger
logger = get_logger(__name__)

logger.info(f"开始处理文件：{filename}")
logger.error(f"错误：{error}")
```

## 日志文件管理

- 日志文件位置：`./logs/AutoVoiceCollation.log`
- 日志会追加到文件末尾（不会覆盖）
- 建议定期清理旧日志文件

## 最佳实践

1. **使用合适的日志级别**
   - `DEBUG`: 仅用于开发调试
   - `INFO`: 记录重要的程序运行状态
   - `WARNING`: 记录潜在问题
   - `ERROR`: 记录错误但不抛出异常
   - `CRITICAL`: 记录严重错误

2. **提供有用的上下文信息**
   ```python
   # 好
   logger.info(f"开始下载视频，URL: {url}, 格式: {format}")

   # 不好
   logger.info("开始下载")
   ```

3. **在异常处理中使用日志**
   ```python
   try:
       process_file(filepath)
   except FileNotFoundError as e:
       logger.error(f"文件不存在: {filepath}, 错误: {e}")
   except Exception as e:
       logger.critical(f"未预期的错误: {e}", exc_info=True)
   ```

## 常见问题

### Q: 为什么看不到 DEBUG 日志？
A: 检查 `LOG_LEVEL` 是否设置为 `'DEBUG'`。

### Q: 如何关闭彩色输出？
A: 设置 `LOG_COLORED_OUTPUT = False`。

### Q: 日志文件太大怎么办？
A: 可以手动删除旧日志，或者实现日志轮转功能（未来版本）。

### Q: 能否为不同模块设置不同的日志级别？
A: 目前所有模块使用相同配置。如需要，可以在 `logger.py` 中扩展功能。
