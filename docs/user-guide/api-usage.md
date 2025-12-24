# AutoVoiceCollation API 使用文档

## 简介

AutoVoiceCollation 提供基于 **FastAPI** 的 HTTP 接口，支持音视频转文本、自动总结与多模式输出，便于与其他系统集成和交互。

> ✅ 基于 [FastAPI](https://fastapi.tiangolo.com/) 构建，具备高性能、自动文档生成、类型校验等特性。

---

## 最新更新

### 🚀 v1.3.0 - 异步推理队列与架构重构

新增功能：

- 🎯 **异步推理队列**：引入 `InferenceQueue` 系统，实现单进程、单模型实例的异步推理，避免 FastAPI 推理阻塞
- 🏗️ **模块化架构**：项目已重构为模块化架构，遵循 SOLID 原则，提高代码可维护性和可扩展性
- ⚡ **性能优化**：推理队列支持串行处理任务，避免 GPU 冲突，提高资源利用率
- 🔧 **统一配置系统**：基于 Pydantic v2 的类型安全配置系统，支持嵌套配置和自动验证

### 🚀 v1.2.0 - 时间戳与 URL/文件名追踪功能

新增功能：

- ✨ **时间戳追踪**：所有任务返回 `created_at`（创建时间）和 `completed_at`（完成时间），单位为 ISO 8601 格式（含微秒）。
- ✨ **URL/文件名追踪**：响应中包含 `url`（B站视频链接）或 `filename`（上传文件名），便于溯源。
- ⚡ **自动端口查找**：启动时自动检测可用端口，避免冲突。
- 📊 **精确处理时长计算**：通过时间差可精准统计任务耗时。

### 📝 v1.1.0 - 文本总结功能

新增功能：

- ✨ **独立总结端点**：`/api/v1/summarize` 可直接对输入文本生成学术风格摘要。
- ✨ **`summarize` 参数支持**：在 `/process` 端点中启用该参数，自动调用 LLM 生成总结。
- 📝 总结采用小论文结构：引言 → 主体 → 结论。
- 🔧 支持自定义 LLM 参数（`temperature`, `max_tokens`）以优化质量。

---

## 启动 API 服务

```bash
# 方式一：直接运行（推荐）
python api.py

# 方式二：使用 uvicorn（适用于开发调试）
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

### 自动端口查找机制

- 若配置端口不可用，自动尝试附近端口（最多 50 次）。
- 可通过 `.env` 文件设置 `WEB_SERVER_PORT` 指定端口。
- 默认端口：`8000`（若被占用则自动切换）。

### 异步推理队列机制

- **设计目标**：解决 FastAPI 推理阻塞问题，实现单进程、单模型实例的异步推理
- **队列容量**：最大 50 个任务，避免积压
- **处理方式**：串行处理任务，避免 GPU 冲突
- **启动时机**：API 服务启动时自动启动推理队列
- **关闭清理**：API 服务关闭时自动停止推理队列并清理资源

#### 启动示例输出：

```
正在启动 AutoVoiceCollation API 服务器...
访问地址: http://127.0.0.1:8073
API 文档: http://127.0.0.1:8073/docs
健康检查: http://127.0.0.1:8073/health
------------------------------------------------------------
INFO:     Uvicorn running on http://127.0.0.1:8073 (Press CTRL+C to quit)
```

> 🌐 访问 `http://localhost:端口号/docs` 查看交互式 API 文档（Swagger UI）。

---

## 任务响应格式（新增字段）

所有任务响应（`TaskResponse`）均包含以下字段：

| 字段名             | 类型     | 说明                          | 示例                                      |
|--------------------|----------|-------------------------------|-------------------------------------------|
| `task_id`          | string   | 任务唯一标识符                 | `"550e8400-e29b-41d4-a716-446655440000"` |
| `status`           | string   | 任务状态：`pending` / `processing` / `completed` / `failed` | `"completed"` |
| `message`          | string   | 状态描述信息                   | `"任务已提交，正在处理中"`                |
| `result`           | object   | 处理结果（仅 `completed` 时存在） | `{...}`                                   |
| `created_at` ⭐     | string   | 任务创建时间（ISO 8601）       | `"2025-10-29T17:35:00.123456"`            |
| `completed_at` ⭐   | string   | 任务完成时间（ISO 8601）       | `"2025-10-29T17:40:30.789012"`            |
| `url` ⭐            | string   | 视频链接（如有）               | `"https://www.bilibili.com/video/BV1xx411c7mu"` |
| `filename` ⭐       | string   | 上传文件名（如有）             | `"audio.mp3"`                             |

> ⭐ 标记为新增字段

---

## 通用说明

### `text_only` 参数（布尔值）

- **默认值**：`false`（生成 PDF、ZIP 等文件）
- **当为 `true` 时**：
  - 不生成 ZIP 包；
  - 仅返回纯文本结果与元数据；
  - `result` 中包含 `raw_text`、`polished_text`、`extract_time`、`polish_time`。

### `summarize` 参数（布尔值）

- **默认值**：`false`（不生成总结）
- **必须配合 `text_only=true` 使用**，否则无效。
- 成功时，`result.summary` 字段将包含学术风格总结。
- 建议使用较高 `temperature`（如 `0.7`）和较大 `max_tokens`（如 `4000`）提升质量。

---

## API 端点列表

### 1. 根端点

- **GET** `/`
- 获取 API 信息与可用端点列表。

#### 示例请求：

```bash
curl http://localhost:8000/
```

#### 响应示例：

```json
{
  "name": "AutoVoiceCollation API",
  "version": "1.0.0",
  "description": "自动语音识别和文本整理服务",
  "endpoints": {
    "docs": "/docs",
    "health": "/health",
    "process_bilibili": "/api/v1/process/bilibili",
    "process_audio": "/api/v1/process/audio",
    "process_batch": "/api/v1/process/batch",
    "process_subtitle": "/api/v1/process/subtitle",
    "summarize": "/api/v1/summarize",
    "task_status": "/api/v1/task/{task_id}",
    "download_result": "/api/v1/download/{task_id}"
  }
}
```

---

### 2. 健康检查

- **GET** `/health`
- 检查服务运行状态与配置。

#### 示例请求：

```bash
curl http://localhost:8000/health
```

#### 响应示例：

```json
{
  "status": "healthy",
  "timestamp": "2025-10-29T17:12:26.789012",
  "config": {
    "asr_model": "paraformer",
    "llm_server": "Cerebras:Qwen-3-235B-Instruct",
    "output_dir": "./out"
  }
}
```

---

### 3. 处理 B站视频

- **POST** `/api/v1/process/bilibili`

#### 请求体（JSON）：

```json
{
  "video_url": "https://www.bilibili.com/video/BV1wP411W7pe",
  "llm_api": "deepseek-chat",
  "temperature": 0.1,
  "max_tokens": 6000,
  "text_only": false,
  "summarize": false
}
```

#### 字段说明：

| 字段 | 类型 | 必需 | 默认 | 说明 |
|------|------|------|------|------|
| `video_url` | string | 是 | —— | 完整 B站视频链接 |
| `llm_api` | string | 否 | 配置文件值 | LLM 服务名称 |
| `temperature` | number | 否 | `0.1` | 控制随机性 |
| `max_tokens` | integer | 否 | `6000` | 输出最大 token 数 |
| `text_only` | boolean | 否 | `false` | 是否仅返回文本 |
| `summarize` | boolean | 否 | `false` | 是否生成总结（需 `text_only=true`） |

#### 响应示例（任务创建）：

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "任务已提交，正在处理中",
  "created_at": "2025-10-29T17:35:00.123456",
  "url": "https://www.bilibili.com/video/BV1wP411W7pe",
  "filename": null,
  "completed_at": null,
  "result": null
}
```

#### 示例 `curl`：

```bash
# 基础用法
curl -X POST "http://localhost:8000/api/v1/process/bilibili" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.bilibili.com/video/BV1wP411W7pe",
    "text_only": true
  }'

# 生成总结
curl -X POST "http://localhost:8000/api/v1/process/bilibili" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.bilibili.com/video/BV1wP411W7pe",
    "text_only": true,
    "summarize": true
  }'
```

---

### 4. 处理音频文件

- **POST** `/api/v1/process/audio`

#### 上传方式：
- 使用 `multipart/form-data`
- 文件字段名为 `file`，支持格式：`mp3`, `wav`, `m4a`, `flac`

#### 其他参数通过表单传递：
- `llm_api`, `temperature`, `max_tokens`, `text_only`, `summarize`

#### 示例 `curl`：

```bash
curl -X POST "http://localhost:8000/api/v1/process/audio" \
  -F "file=@/path/to/audio.mp3" \
  -F "text_only=true" \
  -F "summarize=true"
```

#### 响应示例：

```json
{
  "task_id": "660f9511-f3ac-52e5-b827-557766551111",
  "status": "pending",
  "message": "文件已上传，正在处理中",
  "created_at": "2025-10-29T17:36:00.456789",
  "url": null,
  "filename": "audio.mp3",
  "completed_at": null,
  "result": null
}
```

---

### 5. 批量处理视频

- **POST** `/api/v1/process/batch`

#### 请求体（JSON）：

```json
{
  "urls": [
    "https://www.bilibili.com/video/BV1wP411W7pe",
    "https://www.bilibili.com/video/BV2wQ522X8qf"
  ],
  "llm_api": "deepseek-chat",
  "temperature": 0.1,
  "max_tokens": 6000,
  "text_only": false,
  "summarize": false
}
```

#### 响应示例：

```json
{
  "task_id": "770fa622-g4bd-63f6-c938-668877662222",
  "status": "pending",
  "message": "批量任务已提交，共 2 个视频",
  "created_at": "2025-10-29T17:37:00.789012",
  "url": "https://www.bilibili.com/video/BV1wP411W7pe, https://www.bilibili.com/video/BV2wQ522X8qf",
  "filename": null,
  "completed_at": null,
  "result": null
}
```

> ✅ `text_only` 和 `summarize` 对整个批次统一生效。  
> ✅ `summarize=true` 时，每个视频将单独生成总结。

---

### 6. 生成视频字幕

- **POST** `/api/v1/process/subtitle`

#### 上传方式：
- `multipart/form-data`，字段 `file` 上传视频（支持 `mp4`, `avi`, `mkv`, `mov`）

#### 示例 `curl`：

```bash
curl -X POST "http://localhost:8000/api/v1/process/subtitle" \
  -F "file=@/path/to/video.mp4"
```

#### 响应示例：

```json
{
  "task_id": "880fb733-h5ce-74g7-d049-779988773333",
  "status": "pending",
  "message": "视频已上传，正在生成字幕",
  "created_at": "2025-10-29T17:38:00.111222",
  "url": null,
  "filename": "video.mp4",
  "completed_at": null,
  "result": null
}
```

---

### 7. 文本总结（独立端点）

- **POST** `/api/v1/summarize`

> ❗ 此端点为同步接口，不创建后台任务，处理完成后直接返回结果。

#### 请求体（JSON）：

```json
{
  "text": "这里是需要总结的长文本内容...",
  "title": "文本标题（可选）",
  "llm_api": "deepseek-chat",
  "temperature": 0.7,
  "max_tokens": 4000
}
```

#### 响应示例：

```json
{
  "status": "success",
  "summary": "这是生成的总结内容，以学术风格的小论文形式呈现……",
  "original_length": 5000,
  "summary_length": 800
}
```

#### 示例 `curl`：

```bash
curl -X POST "http://localhost:8000/api/v1/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "这里是一段很长的文本内容……",
    "title": "关于人工智能的思考",
    "llm_api": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 4000
  }'
```

---

### 8. 查询任务状态

- **GET** `/api/v1/task/{task_id}`

#### 示例请求：

```bash
curl http://localhost:8000/api/v1/task/550e8400-e29b-41d4-a716-446655440000
```

#### 响应示例（进行中）：

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "正在下载和处理视频",
  "created_at": "2025-10-29T17:35:00.123456",
  "completed_at": null,
  "url": "https://www.bilibili.com/video/BV1xx411c7mu",
  "filename": null,
  "result": null
}
```

#### 响应示例（已完成，`text_only=true`）：

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "处理完成",
  "created_at": "2025-10-29T17:35:00.123456",
  "completed_at": "2025-10-29T17:40:30.789012",
  "url": "https://www.bilibili.com/video/BV1xx411c7mu",
  "filename": null,
  "result": {
    "title": "视频标题",
    "raw_text": "原始文本...",
    "polished_text": "润色后的文本...",
    "extract_time": 10.5,
    "polish_time": 5.2
  }
}
```

#### 响应示例（`text_only=true` + `summarize=true`）：

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "处理完成",
  "created_at": "2025-10-29T17:35:00.123456",
  "completed_at": "2025-10-29T17:40:30.789012",
  "url": "https://www.bilibili.com/video/BV1xx411c7mu",
  "filename": null,
  "result": {
    "title": "视频标题",
    "raw_text": "原始文本...",
    "polished_text": "润色后的文本...",
    "summary": "这里是LLM生成的学术风格总结……",
    "extract_time": 10.5,
    "polish_time": 5.2
  }
}
```

#### 响应示例（`text_only=false`）：

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "处理完成",
  "created_at": "2025-10-29T17:35:00.123456",
  "completed_at": "2025-10-29T17:40:30.789012",
  "url": "https://www.bilibili.com/video/BV1xx411c7mu",
  "filename": null,
  "result": {
    "output_dir": "./out/20251029_173500",
    "extract_time": 10.5,
    "polish_time": 5.2,
    "zip_file": "./out/20251029_173500.zip"
  }
}
```

---

### 9. 下载处理结果

- **GET** `/api/v1/download/{task_id}`

#### 示例请求：

```bash
curl -O -J http://localhost:8000/api/v1/download/550e8400-e29b-41d4-a716-446655440000
```

> ⚠️ 若任务使用 `text_only=true`，此端点可能返回 `404`。  
> ✅ 请直接从 `/api/v1/task/{task_id}` 的 `result` 中获取文本。

---

## 计算处理时长

使用 `created_at` 和 `completed_at` 计算总耗时。

### Python 示例：

```python
from datetime import datetime

created_at = "2025-10-29T17:35:00.123456"
completed_at = "2025-10-29T17:40:30.789012"

start = datetime.fromisoformat(created_at)
end = datetime.fromisoformat(completed_at)

duration_sec = (end - start).total_seconds()
print(f"处理耗时: {duration_sec:.2f} 秒")  # 输出: 330.67 秒
```

### JavaScript 示例：

```javascript
const createdAt = "2025-10-29T17:35:00.123456";
const completedAt = "2025-10-29T17:40:30.789012";

const startTime = new Date(createdAt);
const endTime = new Date(completedAt);

const durationSec = (endTime - startTime) / 1000;
console.log(`处理耗时: ${durationSec.toFixed(2)} 秒`); // 输出: 330.67 秒
```

---

## Python 客户端示例

### 示例 1：处理 B站视频（完整流程）

```python
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def process_bilibili_video(video_url, text_only=False, summarize=False):
    """处理 B站视频"""
    response = requests.post(
        f"{BASE_URL}/api/v1/process/bilibili",
        json={
            "video_url": video_url.strip(),
            "text_only": text_only,
            "summarize": summarize
        }
    )
    response.raise_for_status()

    task_data = response.json()
    task_id = task_data["task_id"]
    created_at = task_data["created_at"]
    url = task_data["url"]

    print(f"任务已创建: {task_id}")
    print(f"处理的 URL: {url}")
    print(f"创建时间: {created_at}")

    while True:
        status_response = requests.get(f"{BASE_URL}/api/v1/task/{task_id}")
        status_response.raise_for_status()
        status_data = status_response.json()

        status = status_data["status"]
        print(f"当前状态: {status} - {status_data['message']}")

        if status == "completed":
            completed_at = status_data["completed_at"]
            start = datetime.fromisoformat(created_at)
            end = datetime.fromisoformat(completed_at)
            duration = (end - start).total_seconds()

            print(f"\n✓ 处理完成!")
            print(f"  URL: {status_data['url']}")
            print(f"  开始时间: {created_at}")
            print(f"  完成时间: {completed_at}")
            print(f"  总耗时: {duration:.2f} 秒")

            result = status_data["result"]
            if text_only:
                print(f"  标题: {result.get('title', 'N/A')}")
                print(f"  提取时间: {result.get('extract_time', 0):.2f}秒")
                print(f"  润色时间: {result.get('polish_time', 0):.2f}秒")
                if summarize and "summary" in result:
                    print(f"\n学术总结:\n{result['summary'][:500]}...\n")
            else:
                print(f"  输出目录: {result.get('output_dir')}")
                print(f"  ZIP文件: {result.get('zip_file')}")

            break

        elif status == "failed":
            print(f"\n✗ 处理失败: {status_data['message']}")
            break

        time.sleep(5)

if __name__ == '__main__':
    process_bilibili_video(
        "https://www.bilibili.com/video/BV1xx411c7mu",
        text_only=True,
        summarize=True
    )
```

### 示例 2：批量处理并监控进度

```python
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def process_batch_videos(urls, text_only=True, summarize=True):
    response = requests.post(
        f"{BASE_URL}/api/v1/process/batch",
        json={
            "urls": [u.strip() for u in urls],
            "text_only": text_only,
            "summarize": summarize
        }
    )
    response.raise_for_status()

    task_data = response.json()
    task_id = task_data["task_id"]
    created_at = task_data["created_at"]

    print(f"批量任务已创建: {task_id}")
    print(f"视频数量: {len(urls)}")
    print(f"创建时间: {created_at}")

    while True:
        status_response = requests.get(f"{BASE_URL}/api/v1/task/{task_id}")
        status_response.raise_for_status()
        status_data = status_response.json()

        status = status_data["status"]
        print(f"状态: {status} - {status_data['message']}")

        if status == "completed":
            completed_at = status_data["completed_at"]
            start = datetime.fromisoformat(created_at)
            end = datetime.fromisoformat(completed_at)
            duration = (end - start).total_seconds()
            avg_time = duration / len(urls)

            print(f"\n✓ 批量处理完成!")
            print(f"  总耗时: {duration:.2f} 秒")
            print(f"  平均每个视频: {avg_time:.2f} 秒")

            result = status_data["result"]
            if summarize and "summaries" in result:
                print(f"\n生成了 {len(result['summaries'])} 个总结")
                for i, item in enumerate(result['summaries'], 1):
                    print(f"\n--- 视频 {i}: {item.get('title', 'N/A')} ---")
                    print(f"{item.get('summary', 'N/A')[:200]}...")

            break

        elif status == "failed":
            print(f"\n✗ 处理失败: {status_data['message']}")
            break

        time.sleep(10)

if __name__ == '__main__':
    urls = [
        "https://www.bilibili.com/video/BV1111111111",
        "https://www.bilibili.com/video/BV2222222222"
    ]
    process_batch_videos(urls, text_only=True, summarize=True)
```

---

## 配置说明

基于 Pydantic v2 的统一配置系统，配置位于 `.env` 文件或环境变量中：

### 主要配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `WEB_SERVER_PORT` | `8000` | 服务器端口（支持自动查找） |
| `OUTPUT_DIR` | `./out` | 输出文件目录 |
| `TEMP_DIR` | `./temp` | 临时文件目录 |
| `LLM_SERVER` | `Cerebras:Qwen-3-235B-Instruct` | 默认 LLM 服务 |
| `LLM_TEMPERATURE` | `0.1` | LLM 温度参数 |
| `LLM_MAX_TOKENS` | `6000` | LLM 最大 token 数 |
| `ASR_MODEL` | `paraformer` | ASR 模型名称 |
| `OUTPUT_STYLE` | `pdf_only` | 输出样式：`pdf_with_img`, `img_only`, `text_only`, `pdf_only`, `markdown`, `json` |
| `ZIP_OUTPUT_ENABLED` | `false` | 是否输出 zip 压缩包 |
| `ASYNC_FLAG` | `true` | 是否启用异步 LLM 润色 |
| `USE_ONNX` | `false` | 是否启用 ONNX Runtime 推理加速 |
| `DISABLE_LLM_POLISH` | `false` | 是否禁用文本润色 |
| `DISABLE_LLM_SUMMARY` | `false` | 是否禁用摘要生成 |

### 配置架构

项目已重构为模块化配置系统：

```
src/utils/config/
├── base.py          # 配置基类
├── manager.py       # 主配置类 (AppConfig)
├── paths.py         # 路径配置 (PathConfig)
├── llm.py           # LLM 配置 (LLMConfig)
├── asr.py           # ASR 配置 (ASRConfig)
└── logging.py       # 日志配置 (LoggingConfig)
```

### 使用方式

```python
from src.utils.config import get_config

config = get_config()
print(config.web_server_port)  # 访问 Web 服务器端口
print(config.llm.llm_server)   # 访问 LLM 配置
print(config.asr.asr_model)    # 访问 ASR 配置
```

---

## 注意事项

1. **异步处理**：任务为异步执行，需轮询 `/api/v1/task/{task_id}` 获取状态。
2. **时间戳格式**：全部使用 ISO 8601（含微秒），基于服务器本地时间。
3. **URL 与文件名**：
   - 视频处理：`url` 存视频链接，`filename` 为 `null`
   - 文件上传：`filename` 为文件名，`url` 为 `null`
   - 批量任务：多个 URL 用逗号分隔存入 `url`
4. **状态存储**：当前状态存储在内存中，重启后丢失。生产环境建议使用 Redis 或数据库。
5. **`text_only` 模式**：关闭 ZIP/PDF 生成，仅返回文本。
6. **`summarize` 功能**：
   - 必须搭配 `text_only=true` 使用；
   - 调用额外 LLM，增加成本与时间；
   - 建议 `temperature=0.7`, `max_tokens=4000`。
7. **自动端口查找**：启动时自动探测端口，客户端需动态获取实际端口。
8. **推理队列**：
   - 使用异步推理队列处理任务，避免 FastAPI 阻塞
   - 队列容量为 50 个任务，超过限制会拒绝新任务
   - 串行处理任务，确保 GPU 资源不冲突
9. **架构重构**：
   - 项目已从扁平结构重构为模块化架构
   - 配置系统基于 Pydantic v2，支持类型安全和自动验证
   - 使用新的导入路径（如 `from src.utils.config import get_config`）

---

## 错误处理

使用标准 HTTP 状态码：

| 状态码 | 含义 | 响应示例 |
|--------|------|----------|
| `200` | 成功 | `{}` |
| `400` | 请求参数错误 | `{"detail": "Invalid URL format"}` |
| `404` | 资源不存在 | `{"detail": "Task not found"}` |
| `500` | 服务器内部错误 | `{"detail": "Internal server error"}` |

> ✅ 任务失败时，`completed_at` 仍会记录时间戳。

---

## 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [项目 README](../README.md)
- [项目架构文档](../DEVELOPER_GUIDE.md)
- [配置系统文档](../DEVELOPER_GUIDE.md#配置系统)
- [日志配置文档](./LOGGING.md)

---

## 架构迁移说明

项目已从扁平结构（v1）重构为模块化架构（v2）。主要变化：

### 已删除的旧模块
- `src/config.py` → 迁移到 `src/utils/config/`
- `src/core_process.py` → 迁移到 `src/core/processors/`
- `src/extract_audio_text.py` → 迁移到 `src/services/asr/`
- `src/subtitle_generator.py` → 迁移到 `src/services/subtitle/`
- `src/task_manager.py` → 迁移到 `src/utils/helpers/task_manager.py`
- `src/device_manager.py` → 迁移到 `src/utils/device/`
- `src/logger.py` → 迁移到 `src/utils/logging/`

### 新架构优势
1. **单一职责**：每个模块/类有明确的职责
2. **依赖倒置**：高层模块不依赖低层模块，都依赖抽象
3. **开闭原则**：易于扩展新功能（如添加新的 LLM 服务）
4. **接口隔离**：细粒度的接口设计
5. **依赖注入**：通过配置和工厂模式管理依赖

### 迁移指南
1. 更新导入语句，使用新的模块路径
2. 使用新的配置系统（`from src.utils.config import get_config`）
3. 使用新的处理器架构（`src/core/processors/`）
4. 使用新的服务抽象层（`src/services/`）

---

✅ 文档已优化完毕，适合发布至 GitHub Wiki 或内网知识库。
如需导出为 PDF / HTML / Markdown 文件，也可继续协助。
