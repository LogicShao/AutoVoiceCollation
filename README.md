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

1) Python 环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate
pip install -r requirements.txt
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
OUTPUT_STYLE=pdf_only         # pdf_with_img / img_only / text_only / pdf_only / markdown / json
ZIP_OUTPUT_ENABLED=false

# 功能开关
DISABLE_LLM_POLISH=false
DISABLE_LLM_SUMMARY=false
```

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
