# AutoVoiceCollation - 开发者文档（LLM 交互）

本文档专门用于与 LLM 交互时提供详细的技术信息、架构设计和开发指南。

## 项目概述

AutoVoiceCollation 是一个基于 Python 的自动语音识别（ASR）和文本处理工具，结合了语音识别、大语言模型润色和多格式输出等功能。

### 核心技术栈

- **语音识别**: FunASR (SenseVoice/Paraformer 模型)
- **深度学习**: PyTorch, Transformers
- **LLM 集成**: OpenAI API 兼容接口 (DeepSeek, Gemini, Qwen, Cerebras, 本地模型)
- **Web 框架**: FastAPI (API 服务), Gradio (Web UI)
- **文档处理**: ReportLab (PDF 生成), Pillow (图片处理)
- **视频处理**: yt-dlp (视频下载), FFmpeg (音视频处理)
- **配置管理**: python-dotenv
- **异步处理**: asyncio (批量异步文本润色)

## 项目架构

### 1. 模块结构

```
AutoVoiceCollation/
├── config.py                      # 配置管理模块（单例模式）
├── main.py                        # CLI 入口
├── api.py                         # FastAPI RESTful 服务
├── webui.py                       # Gradio Web 界面
│
├── src/                           # 核心代码目录
│   ├── __init__.py
│   ├── Timer.py                   # 计时器工具类
│   ├── logger.py                  # 日志系统（支持彩色输出和文件日志）
│   ├── device_manager.py          # 设备管理（CPU/GPU/ONNX）
│   ├── output_file_manager.py     # 输出文件管理
│   │
│   ├── bilibili_downloader.py     # B站视频下载和音频提取
│   ├── extract_audio_text.py      # ASR 音频转文本（FunASR）
│   ├── core_process.py            # 核心处理流程编排
│   ├── subtitle_generator.py      # 字幕生成和硬编码
│   │
│   ├── text_arrangement/          # 文本处理子模块
│   │   ├── __init__.py
│   │   ├── query_llm.py           # LLM 查询统一接口
│   │   ├── polish_by_llm.py       # LLM 文本润色（支持异步批处理）
│   │   ├── summary_by_llm.py      # LLM 文本摘要
│   │   ├── split_text.py          # 文本分段工具
│   │   └── text_exporter.py       # 文本导出（PDF/图片）
│   │
│   └── SenseVoiceSmall/           # SenseVoice 模型实现
│       ├── __init__.py
│       ├── model.py               # 模型定义
│       ├── ctc_alignment.py       # CTC 对齐
│       └── export_meta.py         # 元数据导出
│
├── tests/                         # 测试目录
│   ├── conftest.py                # pytest 配置
│   └── ...
│
├── .env.example                   # 环境变量配置示例
├── requirements.txt               # Python 依赖
└── README.md                      # 用户文档
```

### 2. 核心处理流程

```
用户输入 (CLI/WebUI/API)
    ↓
[下载/上传阶段]
    ├─ B站视频 → bilibili_downloader.download_bilibili_audio()
    ├─ 本地视频 → bilibili_downloader.extract_audio_from_video()
    └─ 本地音频 → 直接使用
    ↓
[ASR 识别阶段]
    └─ extract_audio_text.extract_audio_text()
       ├─ 加载模型 (SenseVoice/Paraformer)
       ├─ 设备选择 (device_manager)
       └─ 音频转文本
    ↓
[文本处理阶段]
    ├─ split_text() → 文本分段
    ├─ polish_by_llm() → LLM 润色（支持异步）
    │   ├─ 同步模式：顺序处理每段
    │   └─ 异步模式：并发处理多段
    └─ summarize_text() → LLM 摘要生成
    ↓
[输出阶段]
    ├─ text_exporter.text_to_img_or_pdf()
    │   ├─ pdf_with_img: PDF + 图片
    │   ├─ pdf_only: 仅 PDF
    │   ├─ img_only: 仅图片
    │   └─ text_only: JSON 文本
    ├─ subtitle_generator (可选)
    └─ ZIP 压缩（可选）
```

### 3. 配置系统设计

#### config.py 架构

- **环境变量加载**: 使用 `python-dotenv` 从 `.env` 文件加载
- **类型转换与验证**: 自定义 `_get_env()` 函数，支持：
    - 类型转换 (str, int, float, bool, Path)
    - 默认值处理
    - 验证函数 (validate lambda)
- **配置分组**:
    - API Keys (DeepSeek, Gemini, DashScope, Cerebras)
    - 目录配置 (OUTPUT_DIR, DOWNLOAD_DIR, TEMP_DIR, MODEL_DIR, LOG_DIR)
    - 日志配置 (LOG_LEVEL, LOG_FILE, LOG_CONSOLE_OUTPUT, THIRD_PARTY_LOG_LEVEL)
    - ASR 配置 (ASR_MODEL)
    - 设备配置 (DEVICE, USE_ONNX, ONNX_PROVIDERS)
    - LLM 配置 (LLM_SERVER, LLM_TEMPERATURE, LLM_MAX_TOKENS, 等)
    - 功能开关 (DISABLE_LLM_POLISH, DISABLE_LLM_SUMMARY, LOCAL_LLM_ENABLED)

#### 支持的 LLM 服务

```python
LLM_SERVER_SUPPORTED = [
    "qwen3-plus",              # 阿里通义千问 Plus
    "qwen3-max",               # 阿里通义千问 Max
    "deepseek-chat",           # DeepSeek 对话模型
    "deepseek-reasoner",       # DeepSeek 推理模型
    "Cerebras:Qwen-3-32B",     # Cerebras 加速 Qwen 32B
    "Cerebras:Qwen-3-235B-Instruct",  # Cerebras Qwen 235B
    "Cerebras:Qwen-3-235B-Thinking",  # Cerebras Qwen 思考模式
    "gemini-2.0-flash",        # Google Gemini 2.0 Flash
    "local:Qwen/Qwen2.5-1.5B-Instruct",  # 本地模型
]
```

## 关键模块详解

### 1. bilibili_downloader.py

**功能**: B站视频下载和音频提取

**核心类**:

- `BiliVideoFile`: 视频文件元数据容器
    - 属性: `title`, `path`, `bvid`, `url`, `duration`, `owner`
    - 方法: `save_in_json()`, `save_in_text()`

**核心函数**:

- `download_bilibili_audio(url, output_format='mp3', output_dir=DOWNLOAD_DIR)`
    - 使用 yt-dlp 下载 B站视频音频
    - 支持格式: mp3, wav, flac, m4a
    - 返回 `BiliVideoFile` 对象

- `extract_audio_from_video(video_path)`
    - 使用 FFmpeg 从视频中提取音频
    - 输出格式: mp3
    - 返回音频文件路径

**依赖**: yt-dlp, FFmpeg

### 2. extract_audio_text.py

**功能**: 使用 FunASR 进行语音识别

**核心函数**:

- `extract_audio_text(input_audio_path, model_type='paraformer')`
    - 支持模型:
        - `paraformer`: 高准确度，适合中文
        - `sense_voice`: 多语言支持，速度快
    - 设备选择: 通过 `device_manager` 自动检测 GPU/CPU
    - ONNX 支持: 可选 ONNX Runtime 加速
    - 返回文本字符串

**性能优化**:

- `batch_size_s`: 批处理大小（秒），默认值需根据显存调整
- ONNX 推理: 可在 `.env` 中配置 `USE_ONNX=true`

### 3. text_arrangement/query_llm.py

**功能**: 统一的 LLM 查询接口

**设计模式**: 策略模式，支持多种 LLM 服务

**核心函数**:

- `query_llm(prompt, api_service, temperature, max_tokens, ...)`
    - 根据 `api_service` 自动路由到对应的 LLM
    - 统一的错误处理和重试机制
    - 支持的参数: temperature, max_tokens, top_p, top_k

**API 集成**:

- **DeepSeek**: OpenAI 兼容接口
- **Gemini**: Google AI SDK
- **Qwen**: 阿里云 DashScope
- **Cerebras**: 高速推理 API
- **本地模型**: Transformers pipeline

### 4. text_arrangement/polish_by_llm.py

**功能**: 使用 LLM 润色文本

**核心特性**:

- **异步批处理**: 使用 `asyncio` 并发处理多个文本段
- **文本分段**: 自动分段以适应 LLM token 限制
- **合并策略**: 将润色后的段落合并为完整文本

**核心函数**:

- `polish_text(audio_text, api_service, split_len, temperature, max_tokens, async_flag=True, debug_flag=False)`
    - `async_flag=True`: 使用异步并发处理
    - `async_flag=False`: 顺序处理
    - 返回润色后的完整文本

**异步处理流程**:

```python
async def async_polish_text_parts(parts, api_service, ...):
    tasks = [query_llm_async(part, ...) for part in parts]
    return await asyncio.gather(*tasks)
```

### 5. text_arrangement/text_exporter.py

**功能**: 导出文本为 PDF 或图片

**支持格式**:

- `pdf_with_img`: PDF + PNG 图片
- `pdf_only`: 仅 PDF
- `img_only`: 仅 PNG 图片
- `text_only`: JSON 文件

**核心函数**:

- `text_to_img_or_pdf(text, title, output_style, output_path, LLM_info, ASR_model)`
    - PDF 生成: 使用 ReportLab
    - 图片生成: 使用 Pillow
    - 支持中文字体（需要系统字体）

### 6. subtitle_generator.py

**功能**: 字幕生成和视频硬编码

**核心函数**:

- `gen_timestamped_text_file(audio_file)`
    - 生成 SRT 字幕文件
    - 使用 FunASR 的时间戳信息

- `hard_encode_dot_srt_file(video_file, srt_file)`
    - 使用 FFmpeg 将字幕硬编码到视频
    - 返回带字幕的视频文件路径

### 7. logger.py

**功能**: 统一的日志系统

**特性**:

- 多处理器: 控制台 + 文件
- 彩色输出: 使用 colorlog
- 第三方库日志控制: 降低 FunASR/modelscope 等库的日志级别
- 自动创建日志目录

**核心函数**:

- `get_logger(name)`: 获取命名 logger
- `configure_third_party_loggers(log_level)`: 配置第三方库日志级别

## API 服务设计

### FastAPI 架构 (api.py)

#### 任务管理系统

**设计**: 异步任务队列（内存存储）

```python
tasks = {
    "task_id": {
        "status": "pending/processing/completed/failed",
        "message": "...",
        "result": {...},
        "created_at": "2025-10-29T17:35:00.123456",
        "completed_at": "2025-10-29T17:40:30.789012",
        "url": "https://...",  # B站链接
        "filename": "audio.mp3"  # 上传文件名
    }
}
```

#### 核心端点

1. **POST /api/v1/process/bilibili**
    - 请求: `BilibiliVideoRequest`
    - 响应: `TaskResponse` (包含 task_id)
    - 后台任务: `bilibili_video_download_process()`

2. **POST /api/v1/process/audio**
    - 文件上传: `UploadFile`
    - 响应: `TaskResponse`
    - 后台任务: `upload_audio()`

3. **POST /api/v1/process/batch**
    - 批量处理: `BatchProcessRequest`
    - 支持多个 B站链接
    - 后台任务: `process_multiple_urls()`

4. **GET /api/v1/task/{task_id}**
    - 查询任务状态
    - 返回完整的 `TaskResponse`

5. **GET /api/v1/download/{task_id}**
    - 下载处理结果
    - 返回 ZIP 或 PDF 文件

6. **POST /api/v1/summarize**
    - 纯文本摘要服务
    - 请求: `SummarizeRequest`
    - 直接返回摘要结果（无需任务队列）

#### 自动端口发现

```python
def find_available_port(start_port, max_attempts=50):
    """自动查找可用端口"""
    for offset in range(max_attempts):
        port = start_port + offset
        if is_port_available(port):
            return port
    raise RuntimeError("No available port found")
```

### WebUI 设计 (webui.py)

**框架**: Gradio

**界面组件**:

- Tab 1: B站视频处理
- Tab 2: 批量处理
- Tab 3: 本地音频上传
- Tab 4: 本地视频处理
- Tab 5: 字幕生成

**特性**:

- 实时进度显示
- 文件下载
- 参数配置（LLM, temperature, max_tokens）
- `text_only` 模式：仅返回 JSON 结果

## 开发指南

### 1. 环境搭建

```bash
# 克隆项目
git clone https://github.com/LogicShao/AutoVoiceCollation
cd AutoVoiceCollation

# 创建虚拟环境
conda create -n avc_env python=3.11 -y
conda activate avc_env

# 安装依赖
pip install -r requirements.txt

# 安装 PyTorch (CUDA 版本)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu129

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API Keys
```

### 2. 添加新的 LLM 服务

**步骤**:

1. 在 `config.py` 中添加 API Key 配置:

```python
NEW_LLM_API_KEY = _get_env("NEW_LLM_API_KEY", default=None, cast=str)
```

2. 在 `LLM_SERVER_SUPPORTED` 列表中添加服务名:

```python
LLM_SERVER_SUPPORTED = [
    ...,
    "new-llm-service",
]
```

3. 在 `src/text_arrangement/query_llm.py` 中实现查询函数:

```python
def query_new_llm(prompt, temperature, max_tokens, ...):
    # 实现 API 调用逻辑
    return response_text

# 在 query_llm() 中添加路由
if api_service == "new-llm-service":
    return query_new_llm(prompt, temperature, max_tokens, ...)
```

4. 在 `.env.example` 中添加配置说明

### 3. 添加新的 ASR 模型

**步骤**:

1. 在 `src/extract_audio_text.py` 中添加模型加载逻辑:

```python
def extract_audio_text(input_audio_path, model_type='paraformer'):
    if model_type == 'new_model':
        model = AutoModel(model="new-model-name")
    # ...
```

2. 更新配置文档和 `.env.example`

### 4. 测试流程

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_core_process.py

# 查看测试覆盖率
pytest --cov=src tests/
```

### 5. 代码规范

- **命名约定**:
    - 函数: `snake_case`
    - 类: `PascalCase`
    - 常量: `UPPER_CASE`
- **文档字符串**: 使用 docstring 描述函数功能和参数
- **类型提示**: 尽可能使用类型注解
- **错误处理**: 使用 try-except 捕获异常，记录日志

### 6. 日志最佳实践

```python
from src.logger import get_logger

logger = get_logger(__name__)

# 不同级别的日志
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")

# 带异常信息的日志
try:
    risky_operation()
except Exception as e:
    logger.error(f"操作失败: {e}", exc_info=True)
```

## 性能优化建议

### 1. GPU 内存优化

- 降低 `batch_size_s` (在 `extract_audio_text.py` 中)
- 使用 SenseVoiceSmall 而非 Paraformer
- 启用 ONNX 推理 (`USE_ONNX=true`)

### 2. LLM 润色加速

- 启用异步处理: `ASYNC_FLAG=true`
- 调整分段大小: `SPLIT_LIMIT=6000`
- 使用更快的 LLM 服务 (如 Cerebras)

### 3. 文件处理优化

- 启用 ZIP 输出: `ZIP_OUTPUT_ENABLED=true`
- 使用 `text_only` 模式跳过 PDF 生成

## 常见问题解决

### 1. FunASR 模型加载失败

**原因**: 网络问题或缓存损坏

**解决**:

```bash
# 清除模型缓存
rm -rf ~/.cache/modelscope
# 设置镜像（国内）
export MODELSCOPE_CACHE=./models
```

### 2. CUDA Out of Memory

**解决**:

```python
# 在 extract_audio_text.py 中降低 batch_size_s
batch_size_s = 60  # 从默认值降低到 60 或更小
```

### 3. FFmpeg 未找到

**解决**:

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# 下载 FFmpeg 并添加到 PATH
```

### 4. 中文字体缺失

**解决**:

- Linux: 安装 `fonts-wqy-zenhei` 或 `fonts-noto-cjk`
- Windows: 系统自带宋体/微软雅黑
- 在 `text_exporter.py` 中配置字体路径

## 扩展开发

### 添加新的输出格式

**示例**: 添加 Markdown 输出

1. 在 `config.py` 中添加输出格式选项:

```python
OUTPUT_STYLE = _get_env("OUTPUT_STYLE", default="pdf_only", cast=str)
# 支持: pdf_with_img, pdf_only, img_only, text_only, markdown
```

2. 在 `text_exporter.py` 中实现导出函数:

```python
def text_to_markdown(text, title, output_path):
    md_content = f"# {title}\n\n{text}"
    md_file = os.path.join(output_path, f"{title}.md")
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    return md_file
```

3. 在 `text_to_img_or_pdf()` 中添加分支:

```python
if output_style == "markdown":
    return text_to_markdown(text, title, output_path)
```

### 添加数据库支持 (替代内存任务存储)

**推荐**: SQLite 或 PostgreSQL

**实现**:

```python
# api.py
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    task_id = Column(String, primary_key=True)
    status = Column(String)
    created_at = Column(DateTime)
    completed_at = Column(DateTime)
    result = Column(String)  # JSON 字符串

engine = create_engine('sqlite:///tasks.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
```

## 调试技巧

### 1. 启用调试模式

```bash
# 在 .env 中设置
DEBUG_FLAG=true
LOG_LEVEL=DEBUG
```

### 2. 查看第三方库日志

```bash
# 临时启用详细日志
THIRD_PARTY_LOG_LEVEL=DEBUG python main.py
```

### 3. 使用 pdb 调试

```python
import pdb; pdb.set_trace()
```

### 4. 性能分析

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# 你的代码
process_audio(...)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(20)
```

## 版本控制与部署

### Git 工作流

```bash
# 创建新功能分支
git checkout -b feature/new-feature

# 提交更改
git add .
git commit -m "feat: add new feature"

# 推送到远程
git push origin feature/new-feature

# 创建 Pull Request
```

### Docker 部署

**Dockerfile** (示例):

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "api.py"]
```

**docker-compose.yml** (示例):

```yaml
version: '3.8'
services:
  avc-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./out:/app/out
      - ./download:/app/download
    env_file:
      - .env
```

## 安全考虑

1. **API Keys**:
    - 永不提交 `.env` 文件到 Git
    - 使用环境变量或密钥管理服务

2. **文件上传**:
    - 验证文件类型和大小
    - 使用临时目录存储上传文件

3. **LLM 输入**:
    - 清理和验证用户输入
    - 限制文本长度

4. **API 访问**:
    - 添加身份验证（JWT, API Key）
    - 限流和速率限制

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 编写测试
4. 提交 Pull Request
5. 代码审查

## 资源链接

- **项目仓库**: https://github.com/LogicShao/AutoVoiceCollation
- **FunASR 文档**: https://github.com/alibaba-damo-academy/FunASR
- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **Gradio 文档**: https://www.gradio.app/

---

本文档最后更新: 2025-11-04
