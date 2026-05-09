# AutoVoiceCollation

<div align="center">
  <img src="assets/icon.svg" alt="AutoVoiceCollation Icon" width="150" />
</div>

AutoVoiceCollation 是一个面向中文场景的音视频转文本工具，集成 ASR（Paraformer / SenseVoice / whisper.cpp）与 LLM 文本处理能力，支持 CLI、Web 和 REST API 三种使用方式。

## 核心能力

- 多输入源：B站链接、本地音频、本地视频
- 多 ASR 方案：`paraformer`、`sense_voice`、`whisper_cpp`
- 多 LLM 提供商：DeepSeek / Gemini / Qwen / Cerebras / 本地模型
- 多输出形态：`pdf_only`、`pdf_with_img`、`img_only`、`markdown`、`json`、`text_only`
- 异步任务队列：提交任务后立即返回 `task_id`，通过轮询获取结果

## 快速开始

### 方式一：Docker（推荐）

1) 准备配置文件

```bash
git clone https://github.com/LogicShao/AutoVoiceCollation
cd AutoVoiceCollation
cp .env.example .env
```

2) 启动服务

```bash
# Linux / Mac
bash "scripts/docker-start.sh" start

# Windows (PowerShell / CMD)
& "scripts/docker-start.bat" start
```

3) 访问服务

- Web/API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`

### 方式二：本地运行

1) Python 环境 + 前端依赖

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate
pip install -r requirements.txt

# 前端（Tailwind CSS）
npm install
npm run build
```

2) 配置环境变量

```bash
# Linux / Mac
cp .env.example .env
# Windows
copy .env.example .env
```

3) 启动

```bash
# 启动 API + Web
python "api.py"

# CLI（交互模式）
python "main.py"
```

## 使用方式

### CLI

```bash
# 单任务：本地音频
python "main.py" single --audio "/path/to/audio.mp3"

# 单任务：本地视频
python "main.py" single --video "/path/to/video.mp4"

# 单任务：B站链接
python "main.py" single --bili "https://www.bilibili.com/video/BV..."

# 批量任务（文本文件每行一个 URL）
python "main.py" batch --url_file "urls.txt"

# 字幕生成
python "main.py" subtitle --video "/path/to/video.mp4"
```

### API

```bash
python "api.py"
```

主要端点：

- `POST /api/v1/process/bilibili`
- `POST /api/v1/bilibili/check-multipart`
- `POST /api/v1/process/multipart`
- `POST /api/v1/process/audio`
- `POST /api/v1/process/batch`
- `POST /api/v1/process/subtitle`
- `POST /api/v1/summarize`
- `GET /api/v1/task/{task_id}`
- `GET /api/v1/tasks`
- `POST /api/v1/task/{task_id}/cancel`
- `GET /api/v1/download/{task_id}`

完整示例见 `docs/user-guide/api-usage.md`。

## 关键配置（`.env`）

```bash
# ASR
ASR_MODEL=paraformer          # paraformer / sense_voice / whisper_cpp
DEVICE=auto                   # auto / cpu / cuda / cuda:0 ...
USE_ONNX=false

# LLM
LLM_SERVER=Cerebras:Qwen-3-235B-Instruct
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=6000

# 输出
OUTPUT_STYLE=pdf_only         # pdf_with_img / img_only / text_only / pdf_only / markdown / json / mindmap
ZIP_OUTPUT_ENABLED=false

# 功能开关
DISABLE_LLM_POLISH=false
DISABLE_LLM_SUMMARY=false
```

### 支持的 LLM 模型

| 模型标识 | Provider | API Key 字段 |
|---|---|---|
| `deepseek-chat` | DeepSeek | `DEEPSEEK_API_KEY` |
| `deepseek-reasoner` | DeepSeek | `DEEPSEEK_API_KEY` |
| `deepseek-v4-pro` | DeepSeek | `DEEPSEEK_API_KEY` |
| `deepseek-v4-flash` | DeepSeek | `DEEPSEEK_API_KEY` |
| `gemini-2.0-flash` | Google Gemini | `GEMINI_API_KEY` |
| `qwen3-plus` | DashScope (阿里云) | `DASHSCOPE_API_KEY` |
| `qwen3-max` | DashScope (阿里云) | `DASHSCOPE_API_KEY` |
| `Cerebras:Qwen-3-32B` | Cerebras | `CEREBRAS_API_KEY` |
| `Cerebras:Qwen-3-235B-Instruct` | Cerebras | `CEREBRAS_API_KEY` |
| `Cerebras:Qwen-3-235B-Thinking` | Cerebras | `CEREBRAS_API_KEY` |
| `local:Qwen/Qwen2.5-1.5B-Instruct` | 本地 | 需设置 `LOCAL_LLM_ENABLED=true` |

### Whisper.cpp 模型使用指南

whisper.cpp 是 OpenAI Whisper 的 C++ 移植版，无需 GPU、内存占用低、支持多平台。
适合不想安装 PyTorch 或模型文件过大（Paraformer ~2GB）的场景。

#### 1. 下载 whisper.cpp 可执行文件

```bash
# 方式 A：从 GitHub Releases 下载预编译版本
# https://github.com/ggerganov/whisper.cpp/releases
# 选择对应平台（Windows: whisper-cli.exe, Linux: whisper-cli, macOS: whisper-cli）

# 方式 B：自行编译
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
cmake -B build && cmake --build build --config Release
# 编译产物在 build/bin/Release/whisper-cli.exe (Windows) 或 build/bin/whisper-cli (Linux)
```

将可执行文件放到项目 `assets/whisper.cpp/` 目录下（默认路径）。

#### 2. 下载 ggml 模型文件

```bash
# 推荐：medium 模型（1.5GB，中英文平衡，CPU 可运行）
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q5_0.bin

# 其他可选模型（越大精度越高，速度越慢）：
# tiny     (78MB)   - 最快，精度最低
# base     (148MB)  - 快速基准
# small    (488MB)  - 速度与精度平衡
# medium   (1.5GB)  - 推荐，中英文优秀
# large-v3 (3.1GB)  - 最高精度，较慢
```

将模型文件放到 `assets/models/` 目录下（默认路径）。

#### 3. 配置 `.env`

```bash
# 切换 ASR 模型
ASR_MODEL=whisper_cpp

# whisper.cpp 可执行文件路径（留空使用默认：./assets/whisper.cpp/whisper-cli.exe）
WHISPER_CPP_BIN=./assets/whisper.cpp/whisper-cli

# ggml 模型文件路径（留空使用默认：./assets/models/ggml-medium-q5_0.bin）
WHISPER_CPP_MODEL=./assets/models/ggml-medium-q5_0.bin

# 语言（auto 自动检测；zh 强制中文；en 强制英文）
WHISPER_CPP_LANGUAGE=auto

# CPU 线程数（建议设为物理核心数）
WHISPER_CPP_THREADS=4

# 额外参数（原样传给 whisper-cli）
WHISPER_CPP_EXTRA_ARGS=--no-gpu

# VAD（语音活动检测，跳过静音段提升精度，可选）
# WHISPER_CPP_VAD=true
# WHISPER_CPP_VAD_MODEL=./assets/models/ggml-silero-v6.2.0.bin
```

#### 4. 使用

配置完成后正常使用即可，与 paraformer/sense_voice 用法完全一致：

```bash
# CLI
python main.py single --audio "/path/to/audio.mp3"

# API
curl -X POST http://localhost:8000/api/v1/process/audio \
  -F "file=@audio.mp3"
```

#### 5. 性能对比

| 模型 | 大小 | 中文精度 | 速度（CPU, 4线程, 1分钟音频） | 适用场景 |
|---|---|---|---|---|
| `ggml-tiny-q5_0` | 78MB | ★★☆ | ~10s | 实时/快速预览 |
| `ggml-small-q5_0` | 488MB | ★★★ | ~30s | 资源受限设备 |
| `ggml-medium-q5_0` | 1.5GB | ★★★★ | ~60s | **推荐，日常使用** |
| `ggml-large-v3-q5_0` | 3.1GB | ★★★★★ | ~120s | 高精度离线处理 |

## 文档（MVP）

- 文档入口：`docs/README.md`
- Docker 部署：`docs/deployment/docker.md`
- API 使用：`docs/user-guide/api-usage.md`
- 开发指南：`docs/development/developer-guide.md`

## 项目结构（简版）

```text
AutoVoiceCollation/
├── api.py
├── main.py
├── src/
│   ├── api/
│   ├── core/
│   ├── services/
│   ├── text_arrangement/
│   └── utils/
├── frontend/
├── tests/
└── docs/
```

## 开发与测试

```bash
pip install -r requirements-test.txt
pytest
ruff check .
ruff format .
```

## 许可证

MIT License
