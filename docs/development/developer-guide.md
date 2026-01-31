# AutoVoiceCollation - 开发者文档（LLM 交互）

> ✅ 项目版本：v2.0 | LLM 交互模块基于 OpenAI 兼容接口设计，支持多提供商集成

---

## 项目概述

AutoVoiceCollation 是一个基于 Python 的自动语音识别（ASR）与智能文本处理系统，结合 FunASR 与大语言模型（LLM）技术，实现从音视频到精美文档的全流程自动化。

### 🛠️ 核心技术栈
- **ASR**：FunASR（Paraformer / SenseVoice 模型）
- **深度学习**：PyTorch, Transformers
- **LLM 集成**：OpenAI API 兼容接口（DeepSeek, Gemini, Qwen, Cerebras, 本地模型）
- **文档处理**：ReportLab（PDF 生成）、Pillow（图片处理）
- **视频处理**：yt-dlp（视频下载）、FFmpeg（音视频处理）
- **配置管理**：python-dotenv
- **异步处理**：asyncio（批量异步文本润色）

---

## 项目架构

### 1. 模块结构（模块化架构 v2.0）

```bash
AutoVoiceCollation/
├── main.py                        # CLI 入口
├── api.py                         # Web/API 服务
│
├── src/                           # 核心代码目录（模块化架构）
│   ├── api/                       # API 层
│   │   ├── inference_queue.py     # 异步推理队列（解决 FastAPI 阻塞）
│   │   ├── middleware/            # 中间件（错误处理等）
│   │   └── schemas/               # Pydantic 数据模型
│   │
│   ├── core/                      # 核心业务逻辑
│   │   ├── exceptions/            # 异常定义（ASR/LLM/下载/文件/任务）
│   │   ├── export/                # 导出功能（PDF/图片/字幕）
│   │   ├── history/               # 处理历史管理
│   │   ├── models/                # 数据模型
│   │   └── processors/            # 处理器（音频/视频/字幕）
│   │
│   ├── services/                  # 外部服务集成
│   │   ├── asr/                   # ASR 服务（Paraformer/SenseVoice）
│   │   ├── download/              # 下载服务（B站视频下载）
│   │   ├── llm/                   # LLM 服务（多提供商支持）
│   │   └── subtitle/              # 字幕服务
│   │
│   ├── text_arrangement/          # 文本处理
│   │   ├── polish_by_llm.py       # 文本润色
│   │   ├── query_llm.py           # LLM 接口
│   │   ├── split_text.py          # 文本分段
│   │   ├── summary_by_llm.py      # 摘要生成
│   │   └── text_exporter.py       # 导出工具
│   │
│   ├── utils/                     # 工具类
│   │   ├── config/                # 配置管理（基于 Pydantic v2）
│   │   ├── device/                # 设备管理（CPU/GPU/ONNX）
│   │   ├── helpers/               # 辅助工具（任务管理器等）
│   │   └── logging/               # 日志系统
│   │
│   └── SenseVoiceSmall/           # SenseVoice 模型实现
│       ├── __init__.py
│       ├── model.py               # 模型定义
│       ├── ctc_alignment.py       # CTC 对齐
│       └── export_meta.py         # 元数据导出
│
├── tests/                         # 测试目录
│   ├── conftest.py                # pytest 配置
│   ├── test_async_queue.py        # 异步推理队列测试
│   └── ...
│
├── .env.example                   # 环境变量配置示例
├── requirements.txt               # Python 依赖
└── README.md                      # 用户文档
```

### 2. 核心处理流程

```mermaid
graph TD
    A[用户输入 (CLI/Web/API)] --> B[下载/上传阶段]
    B --> C{B站视频}
    B --> D{本地视频}
    B --> E{本地音频}
    
    C --> F[bilibili_downloader.download_bilibili_audio()]
    D --> G[bilibili_downloader.extract_audio_from_video()]
    E --> H[直接使用]
    
    F --> I[ASR 识别阶段]
    G --> I
    H --> I
    
    I --> J[extract_audio_text.extract_audio_text()]
    J --> K{加载模型: Paraformer/SenseVoice}
    K --> L[设备选择: GPU/CPU/ONNX]
    L --> M[音频转文本]
    
    M --> N[文本处理阶段]
    N --> O[split_text() → 文本分段]
    N --> P[polish_by_llm() → LLM 润色]
    N --> Q[summarize_text() → LLM 摘要生成]
    
    P --> R{同步/异步模式}
    R --> S[顺序处理]
    R --> T[并发处理]
    
    O --> U[合并策略]
    Q --> U
    U --> V[输出阶段]
    
    V --> W[text_exporter.text_to_img_or_pdf()]
    V --> X[subtitle_generator (可选)]
    V --> Y[ZIP 压缩 (可选)]
```

### 3. 配置系统设计（基于 Pydantic v2）

#### `src/utils/config/` 架构

- **类型安全配置**：使用 Pydantic v2 进行配置验证和类型转换
- **环境变量自动加载**：支持嵌套配置和自动环境变量映射
- **配置热重载**：支持运行时配置更新
- **配置分组**：
  - `AppConfig`：主配置类，聚合所有子配置
  - `LLMConfig`：LLM 相关配置（API Keys、模型选择、参数）
  - `ASRConfig`：ASR 相关配置（模型选择、批处理大小、设备）
  - `PathConfig`：路径配置（输出目录、缓存目录、模型目录）
  - `LoggingConfig`：日志配置（级别、格式、输出文件）
- **关键配置项**：
  - `ASR_MODEL`：`paraformer`（高精度）或 `sense_voice`（快速/多语言）
  - `LLM_SERVER`：当前使用的 LLM 服务（支持：`deepseek-chat`, `gemini-2.0-flash`, `qwen3-plus`, `Cerebras:*`, `local:*`）
  - `ASYNC_FLAG`：启用异步 LLM 润色（默认 `true`）
  - `DEVICE`：`auto`（自动检测 GPU）、`cpu`、`cuda:0` 等
  - `USE_ONNX`：启用 ONNX Runtime 推理加速
  - `DISABLE_LLM_POLISH` / `DISABLE_LLM_SUMMARY`：功能开关

#### 使用方式
```python
from src.utils.config import get_config

# 获取全局配置
config = get_config()

# 访问配置项
llm_server = config.llm.server  # 如: "deepseek-chat"
asr_model = config.asr.model    # 如: "paraformer"
device = config.device          # 如: "auto"

# 检查功能开关
if not config.llm.disable_polish:
    # 执行 LLM 润色
    pass
```

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

---

## 关键模块详解

### 1. `src/services/download/bilibili_downloader.py`

- **功能**：B站视频下载与音频提取
- **核心类**：
  - `BiliVideoFile`：视频元数据容器
    - 属性：`title`, `path`, `bvid`, `url`, `duration`, `owner`
    - 方法：`save_in_json()`, `save_in_text()`
- **核心函数**：
  - `download_bilibili_audio(url, output_format='mp3', output_dir=DOWNLOAD_DIR)`
    - 使用 `yt-dlp` 下载音频
    - 支持格式：mp3, wav, flac, m4a
    - 返回 `BiliVideoFile` 对象
  - `extract_audio_from_video(video_path)`
    - 使用 `FFmpeg` 提取音频
    - 输出格式：mp3
    - 返回音频路径
- **依赖**：yt-dlp, FFmpeg

### 2. `src/services/asr/`（ASR 服务抽象层）

- **功能**：统一的 ASR 服务接口，支持多种模型
- **支持模型**：
  - `paraformer`：高准确度，适合中文
  - `sense_voice`：多语言支持，速度快
- **核心组件**：
  - `transcriber.py`：ASR 转录器基类和具体实现
  - `preprocess.py`：音频预处理工具
- **设备管理**：通过 `src/utils/device/` 自动检测 GPU/CPU
- **ONNX 支持**：可在 `.env` 中配置 `USE_ONNX=true`
- **性能优化**：
  - `batch_size_s`：批处理大小（秒），需根据显存调整
  - ONNX 推理：启用后可加速推理

### 3. `src/services/llm/`（LLM 服务抽象层）

- **功能**：统一的 LLM 服务接口，支持多提供商
- **设计模式**：工厂模式 + 策略模式
- **核心组件**：
  - `factory.py`：LLM 工厂，根据配置创建对应的 LLM 服务实例
  - `base.py`：抽象基类，定义统一的 LLM 接口
  - 具体实现：`deepseek.py`, `gemini.py`, `qwen.py`, `cerebras.py`, `local.py`
- **支持的服务**：
  - ✅ **DeepSeek**：`deepseek-chat`, `deepseek-reasoner`
  - ✅ **Gemini**：`gemini-2.0-flash`
  - ✅ **Qwen**：`qwen3-plus`, `qwen3-max`
  - ✅ **Cerebras**：`Cerebras:Qwen-3-32B`, `Cerebras:Qwen-3-235B-Instruct`
  - ✅ **本地模型**：`local:Qwen/Qwen2.5-1.5B-Instruct`
- **异步处理**：
  - `polish_by_llm.py` 使用 `asyncio.gather()` 并发调用多个 LLM API
  - 速率限制：`RateLimiter` 类（默认 10 req/min）
  - 重试机制：最多 3 次重试，指数退避 30 秒

### 4. `src/text_arrangement/polish_by_llm.py`

- **功能**：使用 LLM 润色文本
- **核心特性**：
  - ✅ 异步批处理：使用 `asyncio` 并发处理多个文本段
  - ✅ 文本分段：自动分段以适应 LLM token 限制
  - ✅ 合并策略：将润色后的段落合并为完整文本
  - ✅ 任务取消支持：集成任务管理器，支持取消操作
- **核心函数**：
  ```python
  def polish_text(
      audio_text: str,
      api_service: str,
      split_len: int = 6000,
      temperature: float = 0.1,
      max_tokens: int = 4000,
      async_flag: bool = True,
      debug_flag: bool = False,
      task_id: Optional[str] = None  # 新增：支持任务取消
  ) -> str:
      """
      润色文本
      :param async_flag: True = 异步并发处理，False = 顺序处理
      :param task_id: 任务 ID，用于支持任务取消
      :return: 润色后的完整文本
      """
  ```
- **异步处理流程**：
  ```python
  async def async_polish_text_parts(parts: list, api_service: str, **kwargs):
      tasks = [query_llm_async(part, api_service, **kwargs) for part in parts]
      return await asyncio.gather(*tasks)
  ```

### 5. `text_arrangement/text_exporter.py`

- **功能**：导出文本为 PDF 或图片
- **支持格式**：
  - `pdf_with_img`：PDF + PNG 图片
  - `pdf_only`：仅 PDF
  - `img_only`：仅 PNG 图片
  - `text_only`：JSON 文件
  - `markdown`：Markdown 文件
  - `json`：JSON 文件
  - `markdown`：Markdown 文件
  - `json`：JSON 文件
- **核心函数**：
  ```python
  def text_to_img_or_pdf(
      text: str,
      title: str,
      output_style: str,
      output_path: str,
      LLM_info: dict,
      ASR_model: str
  ) -> str:
      """
      导出文本
      :return: 输出文件路径
      """
  ```
- **字体支持**：支持中文字体（需系统安装或指定路径）

### 6. `src/services/subtitle/generator.py`

- **功能**：字幕生成与视频硬编码
- **核心流程**：
  1. ASR 时间戳识别（SenseVoice 或 Paraformer 的时间戳模式）
  2. 文本智能分段（基于停顿阈值 `pause_threshold` 和最大字符数）
  3. LLM 文本匹配和优化（将润色后的文本映射到时间戳）
  4. SRT 字幕生成和视频硬编码（通过 FFmpeg）
- **配置类**：`SubtitleConfig` - 可调节停顿阈值、字符限制、LLM 参数等
- **核心函数**：
  - `generate_subtitle_file()` - 生成 SRT 字幕文件
  - `encode_subtitle_to_video()` - 将字幕烧录到视频
- **返回**：带字幕的视频文件路径

### 7. `src/utils/logging/logger.py`

- **功能**：统一的日志系统
- **特性**：
  - 多处理器：控制台 + 文件
  - 彩色输出：使用 `colorlog`
  - 第三方库日志控制：降低 FunASR/modelscope 等库日志级别
  - 自动创建日志目录
  - 结构化日志输出
- **核心函数**：
  - `get_logger(name)`：获取命名 logger
  - `configure_third_party_loggers(log_level)`：配置第三方库日志级别
- **导入方式**：
  ```python
  from src.utils.logging.logger import get_logger
  logger = get_logger(__name__)
  ```

---

## API 服务设计

### FastAPI 架构 (`api.py`)

#### 任务管理系统

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

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/process/bilibili` | POST | 处理 B站视频 |
| `/api/v1/process/audio` | POST | 处理音频文件 |
| `/api/v1/process/batch` | POST | 批量处理多个 B站链接 |
| `/api/v1/task/{task_id}` | GET | 查询任务状态 |
| `/api/v1/download/{task_id}` | GET | 下载处理结果（ZIP/PDF） |
| `/api/v1/summarize` | POST | 纯文本摘要服务（同步） |

#### 自动端口发现

```python
def find_available_port(start_port: int, max_attempts: int = 50) -> int:
    """自动查找可用端口"""
    for offset in range(max_attempts):
        port = start_port + offset
        if is_port_available(port):
            return port
    raise RuntimeError("No available port found")
```

### Web 前端设计 (`frontend/`)

- **框架**：原生 HTML/CSS/JS + Alpine.js + Tailwind CSS
- **入口**：`frontend/src/index.html` 由 FastAPI `/` 路由返回
- **交互**：`frontend/src/js/main.js` 轮询任务、展示结果、下载文件

---

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

1. 在 `src/utils/config/llm.py` 中添加配置字段：
```python
class LLMConfig(BaseModel):
    # ... 现有配置
    new_llm_api_key: Optional[str] = Field(default=None, env="NEW_LLM_API_KEY")
```

2. 在 `LLM_SERVER_SUPPORTED` 列表中添加服务名：
```python
LLM_SERVER_SUPPORTED = [..., "new-llm-service"]
```

3. 在 `src/services/llm/` 中创建新的 LLM 服务类：
```python
# new_llm.py
from .base import BaseLLMService

class NewLLMService(BaseLLMService):
    async def generate(self, prompt: str, **kwargs) -> str:
        # 实现 API 调用逻辑
        return response_text
```

4. 在 `factory.py` 的 `create_llm_service()` 中添加分支：
```python
def create_llm_service(config: Optional[LLMConfig] = None) -> BaseLLMService:
    # ... 现有逻辑
    if server == "new-llm-service":
        return NewLLMService(config)
```

5. 在 `.env.example` 中添加配置说明

### 3. 添加新的 ASR 模型

1. 在 `src/services/asr/` 中添加新的转录器类：
```python
# new_transcriber.py
from .base import BaseTranscriber

class NewModelTranscriber(BaseTranscriber):
    def __init__(self, config: ASRConfig):
        super().__init__(config)
        # 初始化新模型

    def transcribe(self, audio_path: str) -> str:
        # 实现转录逻辑
        return transcribed_text
```

2. 在 ASR 工厂中添加新模型支持：
```python
# factory.py
def create_transcriber(config: ASRConfig) -> BaseTranscriber:
    if config.model == "new_model":
        return NewModelTranscriber(config)
```

3. 更新配置文档和 `.env.example`

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

- **命名约定**：
  - 函数：`snake_case`
  - 类：`PascalCase`
  - 常量：`UPPER_CASE`
- **文档字符串**：使用 docstring 描述函数功能和参数
- **类型提示**：尽可能使用类型注解
- **错误处理**：使用 try-except 捕获异常，记录日志

### 6. 日志最佳实践

```python
from src.utils.logging.logger import get_logger

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

---

## 性能优化建议

### 1. GPU 内存优化
- 降低 `batch_size_s`（在 ASR 配置中）
- 使用 `SenseVoiceSmall` 而非 `Paraformer`
- 启用 ONNX 推理（`USE_ONNX=true`）
- 使用 `src/utils/device/` 自动检测最佳设备

### 2. LLM 润色加速
- 启用异步处理：`ASYNC_FLAG=true`
- 调整分段大小：`SPLIT_LIMIT=6000`
- 使用更快的 LLM 服务（如 Cerebras）

### 3. 文件处理优化
- 启用 ZIP 输出：`ZIP_OUTPUT_ENABLED=true`
- 使用 `text_only` 模式跳过 PDF 生成

---

## 常见问题解决

### 1. FunASR 模型加载失败
- **原因**：网络问题或缓存损坏
- **解决**：
```bash
rm -rf ~/.cache/modelscope
export MODELSCOPE_CACHE=./models
# 或在 .env 中配置 MODEL_DIR=./models
```

### 2. CUDA Out of Memory
- **解决**：
```python
# 在 ASR 配置中降低 batch_size_s
# 或在 .env 中配置 BATCH_SIZE_S=60
batch_size_s = 60  # 从默认值降低到 60 或更小
```

### 3. FFmpeg 未找到
- **解决**：
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# 下载 FFmpeg 并添加到 PATH
```

### 4. 中文字体缺失
- **解决**：
  - Linux：安装 `fonts-wqy-zenhei` 或 `fonts-noto-cjk`
  - Windows：系统自带宋体/微软雅黑
  - 在 `text_exporter.py` 中配置字体路径

---

## 扩展开发

### 添加新的输出格式（Markdown 示例）

1. 在 `src/utils/config/` 中添加输出选项：
```python
# 在相应的配置类中添加字段
output_style: str = Field(default="pdf_only", env="OUTPUT_STYLE")
# 支持: pdf_with_img, pdf_only, img_only, text_only, markdown, json
```

2. 在 `text_exporter.py` 中实现导出函数：
```python
def text_to_markdown(text, title, output_path):
    md_content = f"# {title}\n\n{text}"
    md_file = os.path.join(output_path, f"{title}.md")
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    return md_file
```

3. 在 `text_to_img_or_pdf()` 中添加分支：
```python
if output_style == "markdown":
    return text_to_markdown(text, title, output_path)
```

---

## 调试技巧

### 1. 启用调试模式
```bash
# 在 .env 中设置
DEBUG_FLAG=true
LOG_LEVEL=DEBUG
```

### 2. 查看第三方库日志
```bash
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

---

## 版本控制与部署

### Git 工作流
```bash
git checkout -b feature/new-feature
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature
```

### Docker 部署
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "api.py"]
```

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

---

## 安全考虑

1. **API Keys**：永不提交 `.env` 文件到 Git
2. **文件上传**：验证文件类型和大小，使用临时目录
3. **LLM 输入**：清理和验证用户输入，限制文本长度
4. **API 访问**：添加身份验证（JWT, API Key）、限流和速率限制

---

## 贡献指南

1. Fork 项目  
2. 创建功能分支  
3. 编写测试  
4. 提交 Pull Request  
5. 代码审查  

---

## 资源链接

- **项目仓库**：[https://github.com/LogicShao/AutoVoiceCollation](https://github.com/LogicShao/AutoVoiceCollation)
- **FunASR 文档**：[https://github.com/alibaba-damo-academy/FunASR](https://github.com/alibaba-damo-academy/FunASR)
- **FastAPI 文档**：[https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)

---

- **最后更新**：2026-01-30
- **文档版本**：2.1（模块化架构更新版）
- **状态**：✅ 已更新，反映当前模块化架构，适用于团队协作与新成员培训

✅ 本文档已优化，适合用于：
- 团队内部培训
- CI/CD 配置
- 新成员入职
- 代码审查与架构评审
