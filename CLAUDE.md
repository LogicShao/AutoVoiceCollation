# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AutoVoiceCollation 是一个 Python 音视频转文本系统，集成 ASR（FunASR）和 LLM（多提供商）进行识别、润色和导出。

**核心技术栈**: FunASR + PyTorch + FastAPI + Gradio + 多 LLM API（DeepSeek/Gemini/Qwen/Cerebras）

## 关键命令

### 环境配置
```bash
# 初始化环境变量（必须）
cp .env.example .env
# 编辑 .env 填入至少一个 LLM API Key

# 安装依赖（不包括 PyTorch）
pip install -r requirements.txt

# 安装 PyTorch（根据你的 CUDA 版本）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu129
```

### 运行服务

```bash
# CLI 交互模式
python main.py

# Web UI（Gradio，默认端口 7860）
python webui.py

# API 服务（FastAPI，默认端口 8000）
python api.py
# API 文档: http://localhost:8000/docs
```

### Docker 部署

```bash
# 一键启动（自动检测 GPU/CPU）
./docker-start.sh start           # Linux/Mac
docker-start.bat start            # Windows

# 手动构建和启动
docker compose build
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

### 测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_api.py

# 运行单个测试
pytest tests/test_api.py::test_health_endpoint -v

# 测试覆盖率
pytest --cov=src tests/

# 跳过慢速/集成测试
pytest -m "not slow and not integration"
```

### 常用开发任务

```bash
# 清理输出和临时文件
python scripts/clear_output.py

# 查看日志
tail -f logs/AutoVoiceCollation.log

# 测试镜像源速度（Docker 构建失败时）
./test-mirrors.bat    # Windows
./test-mirrors.sh     # Linux/Mac
```

## 架构要点

### 核心处理流程

```
输入 → 下载/上传 → ASR 识别 → LLM 润色 → 导出（PDF/图片/字幕）
```

**关键模块**：

- `src/core_process.py` - 流程编排（入口函数）
- `src/extract_audio_text.py` - ASR 识别（FunASR）
- `src/text_arrangement/polish_by_llm.py` - LLM 润色（支持异步批处理）
- `src/text_arrangement/query_llm.py` - LLM 统一接口（策略模式）
- `src/subtitle_generator.py` - 字幕生成和视频硬编码

### 配置系统（config.py）

- **环境变量加载**: `.env` 文件通过 `_get_env()` 加载，支持类型转换和验证
- **关键配置**:
    - `ASR_MODEL`: `paraformer`（高精度）或 `sense_voice`（多语言/快速）
    - `LLM_SERVER`: 当前使用的 LLM 服务（见 `LLM_SERVER_SUPPORTED` 列表）
    - `ASYNC_FLAG`: 启用异步 LLM 润色（默认 `true`）
    - `DEVICE`: `auto`（自动检测）、`cpu`、`cuda`、`cuda:0` 等
    - `USE_ONNX`: 启用 ONNX Runtime 加速

### API 架构（api.py）

- **任务系统**: 内存字典存储 `{task_id: {status, result, ...}}`
- **核心端点**:
    - `POST /api/v1/process/bilibili` - 处理 B站视频
    - `POST /api/v1/process/audio` - 处理音频文件上传
    - `POST /api/v1/process/batch` - 批量处理 B站链接
    - `GET /api/v1/task/{task_id}` - 查询任务状态
    - `GET /api/v1/download/{task_id}` - 下载结果文件
- **后台任务**: 使用 FastAPI `BackgroundTasks` 异步处理

### 任务终止系统（task_manager.py）

- **单例模式**: `get_task_manager()` 获取全局实例
- **功能**: 支持用户主动终止长时间运行的任务（ASR/LLM 处理）
- **检查点**: 在 `core_process.py` 的关键步骤插入 `task_manager.check_cancellation(task_id)`

### LLM 集成策略

- **支持的服务**: DeepSeek, Gemini, Qwen (通义千问), Cerebras, 本地模型
- **异步处理**: `polish_by_llm.py` 使用 `asyncio.gather()` 并发调用 LLM
- **文本分段**: `split_text.py` 将长文本按 `SPLIT_LIMIT` 切分以适应 token 限制

## 开发规范

### 代码风格

- **命名**: 函数 `snake_case`，类 `PascalCase`，常量 `UPPER_CASE`
- **日志**: 使用 `src.logger.get_logger(__name__)`，避免直接 `print()`
- **异常处理**: 捕获异常并记录详细日志（`logger.error(msg, exc_info=True)`）

### 日志使用
```python
from src.logger import get_logger
logger = get_logger(__name__)

logger.debug("详细调试信息")
logger.info("一般流程信息")
logger.warning("潜在问题警告")
logger.error("错误信息", exc_info=True)  # 包含堆栈
```

### 添加新 LLM 服务

1. 在 `config.py` 添加 `NEW_LLM_API_KEY` 和更新 `LLM_SERVER_SUPPORTED`
2. 在 `src/text_arrangement/query_llm.py` 实现 `query_new_llm()` 函数
3. 在 `query_llm()` 添加路由：`if api_service == "new-service": ...`
4. 更新 `.env.example` 文档

### 测试编写

- **测试标记**: 使用 `@pytest.mark.integration` / `@pytest.mark.slow` / `@pytest.mark.unit`
- **Fixture**: 常用 fixture 在 `tests/conftest.py`
- **Mock**: 使用 `pytest-mock` 或 `responses` 库 mock 外部 API
- **异步测试**: 使用 `@pytest.mark.asyncio` 装饰器

## 常见问题处理

### Docker 构建网络问题

**症状**: `Connection failed` 或 `502 Bad Gateway` 错误

**解决**:

1. 运行 `./test-mirrors.bat` 测试镜像源
2. 修改 `Dockerfile` 第 21-22 行切换镜像源（清华/阿里云/中科大）
3. 或使用代理：设置 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量
4. 详见 `docs/DOCKER_NETWORK_FIX.md`

### GPU 内存不足（CUDA OOM）
**解决**:

- 降低 `batch_size_s`（在 `extract_audio_text.py` 中）
- 切换到 `sense_voice` 模型（更轻量）
- 启用 ONNX：`.env` 设置 `USE_ONNX=true`
- 或强制使用 CPU：`DEVICE=cpu`

### FunASR 模型下载慢
**解决**:

- 设置 `MODEL_DIR=./models` 手动下载模型到本地
- 或设置 `MODELSCOPE_CACHE` 环境变量指向缓存目录

### 测试失败排查

1. 检查 `.env` 是否配置（至少一个 LLM API Key）
2. 运行 `pytest -v -s` 查看详细输出
3. 使用 `pytest --lf` 仅运行上次失败的测试
4. 检查 `logs/AutoVoiceCollation.log` 日志文件

## 重要文件位置

- **配置**: `config.py`, `.env.example`
- **主入口**: `main.py` (CLI), `webui.py` (Web UI), `api.py` (API)
- **核心逻辑**: `src/core_process.py`
- **LLM 接口**: `src/text_arrangement/query_llm.py`
- **测试**: `tests/` (pytest 配置在 `pytest.ini`)
- **文档**: `docs/` (API 文档、Docker 指南等)
- **Docker**: `Dockerfile`, `docker-compose.yml`, `docker-start.sh/.bat`

## 项目约定

1. **不提交 `.env` 文件**: 包含敏感 API Keys，已在 `.gitignore`
2. **输出目录**: `out/`, `download/`, `temp/`, `logs/` 不提交（gitignored）
3. **模型缓存**: 默认使用系统缓存（`~/.cache/modelscope`），可通过 `MODEL_DIR` 覆盖
4. **端口**: WebUI 默认 7860，API 默认 8000，Docker GPU 版本 7860，CPU 版本 7861
5. **Python 版本**: 3.11+（兼容 PyTorch 和 FunASR）
6. **代码注释**: 始终与现有代码库注释语言保持一致（自动检测），确保代码库语言统一

## 外部依赖

- **FFmpeg**: 音视频处理（系统级依赖，需手动安装）
- **中文字体**: PDF 生成需要系统中文字体（Linux: `fonts-wqy-zenhei`）
- **yt-dlp**: B站视频下载
- **GPU 驱动**: CUDA 12.4+（可选，用于 GPU 加速）

---

**详细开发文档**: 查看 `docs/DEVELOPER_GUIDE.md`（原 CLAUDE.md 完整版）
