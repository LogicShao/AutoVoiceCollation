# AutoVoiceCollation API 使用文档

## 简介

AutoVoiceCollation 提供了基于 FastAPI 的 HTTP 接口，方便与其他程序进行集成和交互。

## 最新更新

### v1.2.0 - 时间戳和 URL 追踪功能

新增功能：

- ✨ **时间戳追踪**：所有任务现在返回 `created_at`（创建时间）和 `completed_at`（完成时间）
- ✨ **URL/文件名追踪**：任务响应包含 `url`（视频链接）或 `filename`（上传的文件名）
- ⚡ **自动端口查找**：API 服务器启动时自动查找可用端口，避免端口冲突
- 📊 **处理时长计算**：通过时间戳可以精确计算任务处理耗时

### v1.1.0 - 文本总结功能

新增功能：

- ✨ **独立总结端点** `/api/v1/summarize`：直接对文本进行学术风格的总结
- ✨ **summarize 参数**：在处理端点中添加 `summarize` 参数，自动对处理结果生成总结
- 📝 总结采用学术小论文格式，包含引言、主体和结论
- 🔧 支持自定义 LLM 参数（temperature、max_tokens）以优化总结质量

## 启动 API 服务

```bash
# 方式1：直接运行（推荐）
python api.py

# 方式2：使用 uvicorn
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

### 自动端口查找

API 服务器启动时会自动检测端口是否可用：

- 如果配置的端口不可用，会自动查找附近的可用端口
- 支持在 `.env` 文件中设置 `WEB_SERVER_PORT` 指定端口
- 默认端口：8000（如果不可用会自动切换）

启动示例输出：

```
正在启动 AutoVoiceCollation API 服务器...
访问地址: http://127.0.0.1:8073
API 文档: http://127.0.0.1:8073/docs
健康检查: http://127.0.0.1:8073/health
------------------------------------------------------------
INFO:     Uvicorn running on http://127.0.0.1:8073 (Press CTRL+C to quit)
```

访问 `http://localhost:端口号/docs` 查看交互式 API 文档（Swagger UI）。

## 任务响应格式（新增字段）

所有任务响应（`TaskResponse`）现在包含以下字段：

| 字段名                  | 类型     | 说明            | 示例                                                     |
|----------------------|--------|---------------|--------------------------------------------------------|
| `task_id`            | string | 任务唯一标识符       | `"550e8400-e29b-41d4-a716-446655440000"`               |
| `status`             | string | 任务状态          | `"pending"`, `"processing"`, `"completed"`, `"failed"` |
| `message`            | string | 状态消息          | `"任务已提交，正在处理中"`                                        |
| `result`             | object | 处理结果（仅完成时）    | `{...}`                                                |
| **`created_at`** ⭐   | string | 任务创建时间（ISO格式） | `"2025-10-29T17:35:00.123456"`                         |
| **`completed_at`** ⭐ | string | 任务完成时间（ISO格式） | `"2025-10-29T17:40:30.789012"`                         |
| **`url`** ⭐          | string | 处理的视频URL（如果有） | `"https://www.bilibili.com/video/BV1xx411c7mu"`        |
| **`filename`** ⭐     | string | 上传的文件名（如果有）   | `"audio.mp3"`                                          |

⭐ 标记为新增字段

## 通用说明

- **text_only 参数**（布尔）：如果为 `true`，处理过程只返回纯文本结果（以及处理信息元数据），不会生成 PDF、ZIP 或其它文档格式的输出文件。
    - 默认行为：`text_only=false`（仍会生成 PDF、ZIP 等文件并在下载端点提供下载）。
    - 当使用 `text_only=true` 时：处理完成后，任务的 `result` 字段将包含文本内容与若干处理时长/路径信息；不会生成 zip 下载包。

- **summarize 参数**（布尔）：如果为 `true`，系统会在处理完成后调用 LLM 对润色后的文本进行总结，生成学术风格的小论文摘要。
    - 默认行为：`summarize=false`（不生成总结）。
    - **必须配合 `text_only=true` 使用**：只有在 `text_only=true` 模式下，`summarize` 参数才会生效。
    - 总结结果会添加到任务 `result` 的 `summary` 字段中。

## API 端点

### 1. 根端点

**GET** `/`

获取 API 信息和所有可用端点列表。

示例：

```bash
curl http://localhost:8000/
```

响应示例：

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

**GET** `/health`

检查服务运行状态和配置信息。

示例：

```bash
curl http://localhost:8000/health
```

响应示例：

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

### 3. 处理 B 站视频

**POST** `/api/v1/process/bilibili`

提交 B 站视频处理任务。

请求 JSON 字段：

```json
{
  "video_url": "https://www.bilibili.com/video/BV1...",
  "llm_api": "deepseek-chat",
  "temperature": 0.1,
  "max_tokens": 6000,
  "text_only": false,
  "summarize": false
}
```

字段说明：

- `video_url`：B 站视频完整链接（必需）
- `llm_api`：要使用的 LLM 服务（可选，默认：配置文件中的值）
- `temperature`：LLM 温度参数（可选，默认：`0.1`）
- `max_tokens`：生成文本时的最大 token 数（可选，默认：`6000`）
- `text_only`：是否只返回纯文本结果（可选，默认：`false`）
- `summarize`：是否生成文本总结（可选，默认：`false`，**需要配合 `text_only=true` 使用**）

响应示例（任务创建）：

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "任务已提交，正在处理中",
  "created_at": "2025-10-29T17:35:00.123456",
  "url": "https://www.bilibili.com/video/BV1xx411c7mu",
  "filename": null,
  "completed_at": null,
  "result": null
}
```

示例 curl：

```bash
# 基本用法
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

**POST** `/api/v1/process/audio`

上传并处理音频文件。

上传与参数说明：
- `file`: 音频文件，通过 multipart/form-data 的 `file` 字段上传（支持 mp3, wav, m4a, flac）。
- 其它参数：`llm_api`、`temperature`、`max_tokens`、`text_only`、`summarize` 通过表单字段传递。

示例 curl：

```bash
curl -X POST "http://localhost:8000/api/v1/process/audio" \
  -F "file=@/path/to/audio.mp3" \
  -F "text_only=true" \
  -F "summarize=true"
```

响应示例：

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

**POST** `/api/v1/process/batch`

批量处理多个 B 站视频。

请求体示例：

```json
{
  "urls": [
    "https://www.bilibili.com/video/BV1...",
    "https://www.bilibili.com/video/BV2..."
  ],
  "llm_api": "deepseek-chat",
  "temperature": 0.1,
  "max_tokens": 6000,
  "text_only": false,
  "summarize": false
}
```

响应示例：

```json
{
  "task_id": "770fa622-g4bd-63f6-c938-668877662222",
  "status": "pending",
  "message": "批量任务已提交，共 2 个视频",
  "created_at": "2025-10-29T17:37:00.789012",
  "url": "https://www.bilibili.com/video/BV1..., https://www.bilibili.com/video/BV2...",
  "filename": null,
  "completed_at": null,
  "result": null
}
```

说明：

- `text_only` 和 `summarize` 可对整个批次统一控制（true/false）。
- 当 `summarize=true` 且 `text_only=true` 时，会对每个视频的文本分别生成总结。
- 多个 URL 在 `url` 字段中用逗号分隔。

---

### 6. 生成视频字幕

**POST** `/api/v1/process/subtitle`

为视频生成字幕并硬编码。

表单数据：
- `file`: 视频文件（通过 multipart/form-data 的 `file` 字段上传，支持 mp4, avi, mkv, mov）。

示例 curl：

```bash
curl -X POST "http://localhost:8000/api/v1/process/subtitle" \
  -F "file=@/path/to/video.mp4"
```

响应示例：

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

### 7. 文本总结

**POST** `/api/v1/summarize`

直接对文本进行总结，生成学术风格的小论文。此端点不涉及音视频处理，仅接收文本并返回总结结果。

请求体示例：

```json
{
  "text": "这里是需要总结的长文本内容...",
  "title": "文本标题（可选）",
  "llm_api": "deepseek-chat",
  "temperature": 0.7,
  "max_tokens": 4000
}
```

响应示例（同步返回）：

```json
{
  "status": "success",
  "summary": "这是生成的总结内容，以学术风格的小论文形式呈现...",
  "original_length": 5000,
  "summary_length": 800
}
```

示例 curl：

```bash
curl -X POST "http://localhost:8000/api/v1/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "这里是一段很长的文本内容...",
    "title": "关于人工智能的思考",
    "llm_api": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 4000
  }'
```

注意：此端点是**同步的**，不会创建后台任务，处理完成后直接返回结果。

---

### 8. 查询任务状态

**GET** `/api/v1/task/{task_id}`

查询任务处理状态以及结果。

示例：

```bash
curl http://localhost:8000/api/v1/task/550e8400-e29b-41d4-a716-446655440000
```

响应示例（处理中）：

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

响应示例（已完成，text_only=true）：

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

响应示例（已完成，text_only=true 且 summarize=true）：

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
    "summary": "这里是LLM生成的学术风格总结...",
    "extract_time": 10.5,
    "polish_time": 5.2
  }
}
```

响应示例（已完成，text_only=false）：

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

**GET** `/api/v1/download/{task_id}`

下载任务处理结果（ZIP 文件）。

示例：

```bash
curl -O -J http://localhost:8000/api/v1/download/550e8400-e29b-41d4-a716-446655440000
```

说明：如果任务是使用 `text_only=true` 提交的，则该端点可能返回 404；请直接在 `/api/v1/task/{task_id}` 的 `result` 中获取文本结果。

---

## 计算处理时长

使用 `created_at` 和 `completed_at` 来计算处理总时长：

### Python 示例：

```python
from datetime import datetime

# 从 API 响应获取时间戳
created_at = "2025-10-29T17:35:00.123456"
completed_at = "2025-10-29T17:40:30.789012"

# 解析时间戳
start_time = datetime.fromisoformat(created_at)
end_time = datetime.fromisoformat(completed_at)

# 计算处理时长
duration = end_time - start_time
print(f"处理耗时: {duration.total_seconds():.2f} 秒")
# 输出: 处理耗时: 330.67 秒
```

### JavaScript 示例：

```javascript
const createdAt = "2025-10-29T17:35:00.123456";
const completedAt = "2025-10-29T17:40:30.789012";

const startTime = new Date(createdAt);
const endTime = new Date(completedAt);

const durationMs = endTime - startTime;
const durationSec = durationMs / 1000;

console.log(`处理耗时: ${durationSec.toFixed(2)} 秒`);
// 输出: 处理耗时: 330.67 秒
```

---

## Python 客户端示例

### 示例 1：处理 B站视频（完整工作流程）

```python
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def process_bilibili_video(video_url, text_only=False, summarize=False):
    """处理 B站视频"""
    # 1. 提交任务
    response = requests.post(
        f"{BASE_URL}/api/v1/process/bilibili",
        json={
            "video_url": video_url,
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

    # 2. 轮询任务状态
    while True:
        status_response = requests.get(f"{BASE_URL}/api/v1/task/{task_id}")
        status_response.raise_for_status()
        status_data = status_response.json()

        status = status_data["status"]
        print(f"当前状态: {status} - {status_data['message']}")

        if status == "completed":
            completed_at = status_data["completed_at"]

            # 计算处理时长
            start = datetime.fromisoformat(created_at)
            end = datetime.fromisoformat(completed_at)
            duration = (end - start).total_seconds()

            print(f"\n✓ 处理完成!")
            print(f"  URL: {status_data['url']}")
            print(f"  开始时间: {created_at}")
            print(f"  完成时间: {completed_at}")
            print(f"  总耗时: {duration:.2f} 秒")

            # 显示结果
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

# 使用示例
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
    """批量处理视频"""
    # 提交批量任务
    response = requests.post(
        f"{BASE_URL}/api/v1/process/batch",
        json={
            "urls": urls,
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

    # 轮询任务状态
    while True:
        status_response = requests.get(f"{BASE_URL}/api/v1/task/{task_id}")
        status_response.raise_for_status()
        status_data = status_response.json()

        status = status_data["status"]
        print(f"状态: {status} - {status_data['message']}")

        if status == "completed":
            completed_at = status_data["completed_at"]

            # 计算处理时长
            start = datetime.fromisoformat(created_at)
            end = datetime.fromisoformat(completed_at)
            duration = (end - start).total_seconds()

            print(f"\n✓ 批量处理完成!")
            print(f"  总耗时: {duration:.2f} 秒")
            print(f"  平均每个视频: {duration / len(urls):.2f} 秒")

            # 显示总结（如果有）
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

# 使用示例
if __name__ == '__main__':
    urls = [
        "https://www.bilibili.com/video/BV1111111111",
        "https://www.bilibili.com/video/BV2222222222"
    ]
    process_batch_videos(urls, text_only=True, summarize=True)
```

---

## 配置说明

API 服务使用项目根目录下的 `config.py` 中的配置，可以通过修改 `.env` 文件来调整：

- `WEB_SERVER_PORT`: Web 服务器端口（默认：`8000`，支持自动查找可用端口）
- `OUTPUT_DIR`: 输出目录（默认：`./out`）
- `TEMP_DIR`: 临时文件目录（默认：`./temp`）
- `LLM_SERVER`: 默认 LLM 服务（默认：`Cerebras:Qwen-3-235B-Instruct`）
- `LLM_TEMPERATURE`: LLM 温度参数（默认：`0.1`）
- `LLM_MAX_TOKENS`: LLM 最大 token 数（默认：`6000`）
- `ASR_MODEL`: ASR 模型（默认：`paraformer`）

---

## 注意事项

1. **任务处理**：任务是异步处理的，需要通过轮询 `/api/v1/task/{task_id}` 端点来获取处理状态。

2. **时间戳格式**：所有时间戳都使用 ISO 8601 格式（带微秒），基于服务器本地时间。

3. **URL 和文件名**：
    - 对于视频处理，`url` 字段包含视频链接，`filename` 为 `null`
    - 对于文件上传，`filename` 包含文件名，`url` 为 `null`
    - 批量任务的多个 URL 用逗号分隔存储在 `url` 字段中

4. **任务状态存储**：当前任务状态存储在内存中，服务重启后任务状态会丢失。生产环境建议使用 Redis 或数据库。

5. **text_only 模式**：
    - 当使用 `text_only=true` 时，系统不会生成 PDF/ZIP 等文件，仅返回文本。
    - 如果需要持久化文件，请把 `text_only` 设为 `false`（默认）。

6. **summarize 功能**：
    - `summarize` 参数**必须配合 `text_only=true` 使用**，否则不会生效。
    - 总结功能会额外调用一次 LLM API，会增加处理时间和成本。
    - 建议使用较高的 `temperature`（如 0.7）和较大的 `max_tokens`（如 4000）。

7. **自动端口查找**：
    - API 启动时会自动检测端口是否可用
    - 如果配置的端口不可用，会自动查找附近的可用端口（最多尝试 50 个）
    - 确保在客户端代码中使用实际的端口号

---

## 错误处理

API 使用标准 HTTP 状态码：

- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

错误响应示例：

```json
{
  "detail": "错误描述信息"
}
```

任务失败时，`completed_at` 仍然会被设置：

```json
{
  "task_id": "880fb733-h5ce-74g7-d049-779988773333",
  "status": "failed",
  "message": "处理失败: 视频下载失败",
  "created_at": "2025-10-29T17:38:00.111222",
  "completed_at": "2025-10-29T17:38:15.333444",
  "url": "https://www.bilibili.com/video/INVALID",
  "filename": null,
  "result": null
}
```

---

## 参考资料

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [项目 README](../README.md)
- [日志配置文档](./LOGGING.md)
