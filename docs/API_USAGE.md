# AutoVoiceCollation API 使用文档

## 简介

AutoVoiceCollation 提供了基于 FastAPI 的 HTTP 接口，方便与其他程序进行集成和交互。文档包含常用端点说明、参数与示例调用方式。

## 启动 API 服务

```bash
# 方式1：直接运行
python api.py

# 方式2：使用 uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

访问 `http://localhost:8000/docs` 查看交互式 API 文档（Swagger UI）。

## 通用说明

- 新增参数 `text_only`（布尔）：如果为 `true`，处理过程只返回纯文本结果（以及处理信息元数据），不会生成 PDF、ZIP 或其它文档格式的输出文件。
- 默认行为：`text_only=false`（仍会生成 PDF、ZIP 等文件并在下载端点提供下载）。
- 当使用 `text_only=true` 时：
  - 处理完成后，任务的 `result` 字段将包含 `text`（合并/润色后的纯文本）与若干处理时长/路径信息；不会生成 zip 下载包。
  - 如果需要持久化文件（例如 PDF），请把 `text_only` 设为 `false`（默认）。

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
  "timestamp": "2025-10-27T12:34:56.789012",
  "config": {
    "asr_model": "paraformer",
    "llm_server": "deepseek-chat",
    "output_dir": "./out"
  }
}
```

---

### 3. 处理 B 站视频

**POST** `/api/v1/process/bilibili`

提交 B 站视频处理任务。

请求 JSON 字段（示例）：

```json
{
  "video_url": "https://www.bilibili.com/video/BV1...",
  "llm_api": "deepseek-chat",
  "temperature": 0.1,
  "max_tokens": 6000,
  "text_only": false
}
```

字段说明：
- `video_url`：B 站视频完整链接
- `llm_api`：要使用的 LLM 服务（默认：`deepseek-chat`）
- `temperature`：LLM 温度参数
- `max_tokens`：生成文本时的最大 token 数
- `text_only`：是否只返回纯文本结果（可选，默认 false）

响应示例（任务提交）：

```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "任务已提交，正在处理中"
}
```

示例 curl：

```bash
curl -X POST "http://localhost:8000/api/v1/process/bilibili" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.bilibili.com/video/BV1234567890",
    "llm_api": "deepseek-chat",
    "temperature": 0.1,
    "max_tokens": 6000,
    "text_only": true
  }'
```

---

### 4. 处理音频文件

**POST** `/api/v1/process/audio`

上传并处理音频文件。

上传与参数说明：
- `file`: 音频文件，通过 multipart/form-data 的 `file` 字段上传（支持 mp3, wav, m4a, flac）。
- 其它参数：`llm_api`、`temperature`、`max_tokens`、`text_only` 在当前 `api.py` 实现中被声明为普通参数并具有默认值，因此请通过 URL 查询参数传递（可选），例如：
  `?llm_api=deepseek-chat&temperature=0.1&max_tokens=6000&text_only=true`。

示例 curl（将参数放到查询字符串并在表单中上传文件）：

```bash
curl -X POST "http://localhost:8000/api/v1/process/audio?llm_api=deepseek-chat&temperature=0.1&max_tokens=6000&text_only=true" \
  -F "file=@/path/to/audio.mp3"
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
  "text_only": false
}
```

说明：`text_only` 可对整个批次统一控制（true/false）。

---

### 6. 生成视频字幕（并硬编码）

**POST** `/api/v1/process/subtitle`

为视频生成字幕并可选择硬编码。

表单数据：
- `file`: 视频文件（通过 multipart/form-data 的 `file` 字段上传，支持 mp4, avi, mkv, mov）。

注意：当前 `api.py` 的 `process_video_subtitle` 端点实现仅接受视频文件（和后台任务处理）；并不接收 `text_only` 等控制参数。如果你在 Web UI 中勾选 `text_only`，该字段不会被用于该字幕端点的后端处理（请在前端避免对该端点传递 `text_only`）。

示例 curl：

```bash
curl -X POST "http://localhost:8000/api/v1/process/subtitle" \
  -F "file=@/path/to/video.mp4"
```

---

### 7. 查询任务状态

**GET** `/api/v1/task/{task_id}`

查询任务处理状态以及结果。

示例：

```bash
curl http://localhost:8000/api/v1/task/your-task-id
```

响应示例（处理完成且默认输出文件的情况）：

```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "message": "处理完成",
  "result": {
    "output_dir": "./out/filename",
    "extract_time": 10.5,
    "polish_time": 5.2,
    "zip_file": "./out/filename.zip"
  }
}
```

响应示例（`text_only=true` 的情况）：

```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "message": "处理完成",
  "result": {
    "text": "这里是合并并润色后的纯文本内容...",
    "extract_time": 10.5,
    "polish_time": 5.2
  }
}
```

说明：当 `text_only=true` 时 `result` 中会包含 `text` 字段（字符串），且通常不会包含 `zip_file` 字段。

---

### 8. 下载处理结果

**GET** `/api/v1/download/{task_id}`

下载任务处理结果（ZIP 文件）。

示例：

```bash
curl -O -J http://localhost:8000/api/v1/download/your-task-id
```

说明：如果任务是使用 `text_only=true` 提交并且服务未生成 zip 包，则该下载端点可能返回 404 或空内容；请直接在 `/api/v1/task/{task_id}` 的 `result.text` 中获取纯文本结果。

## Web UI（`webui.py`）说明

- 在每个处理 Tab（例如 B 站、音频、批量、字幕）中已加入 `text_only` 复选框控件。
- 在 Web UI 中勾选 `text_only` 后，前端会在请求体/表单中传递 `text_only=true` 到后端，下游处理流程将遵循同样的行为（只返回纯文本并跳过 PDF/ZIP 生成）。
- 特别说明：字幕端点 `/api/v1/process/subtitle` 在当前后端实现中不读取 `text_only`，前端应避免对该端点传递该参数。
- 如果需要下载文件（PDF/ZIP），请确保在 UI 中不勾选 `text_only`。

## Python 客户端示例

```python
import requests
import time

BASE_URL = "http://localhost:8000"

def process_bilibili_video(video_url, text_only=False):
    # 提交任务
    response = requests.post(
        f"{BASE_URL}/api/v1/process/bilibili",
        json={
            "video_url": video_url,
            "llm_api": "deepseek-chat",
            "temperature": 0.1,
            "max_tokens": 6000,
            "text_only": text_only
        }
    )
    response.raise_for_status()
    task_id = response.json()["task_id"]
    print(f"任务已提交，ID: {task_id}")

    # 轮询任务状态
    while True:
        status_response = requests.get(f"{BASE_URL}/api/v1/task/{task_id}")
        status_response.raise_for_status()
        status_data = status_response.json()
        status = status_data["status"]
        print(f"任务状态: {status} - {status_data.get('message')}")

        if status == "completed":
            print("处理完成！")
            result = status_data.get("result", {})

            # 如果是 text_only 模式：从 result.text 中获取纯文本
            if text_only:
                text = result.get("text")
                if text is not None:
                    print("纯文本结果:\n", text[:1000])
                else:
                    print("未在 result 中找到 text 字段，可能已生成文件，请检查 download 端点")
            else:
                # 非 text_only：可能会返回 zip_file 路径，可通过 download 端点或返回的 zip_file 字段下载
                zip_file = result.get("zip_file")
                if zip_file:
                    print("生成了 zip 文件：", zip_file)
                    # 也可以使用 /api/v1/download/{task_id} 下载
                else:
                    print("未返回 zip_file 字段，请检查 task.result")
            break
        elif status == "failed":
            print(f"处理失败: {status_data.get('message')}")
            break

        time.sleep(5)

# 使用示例
if __name__ == '__main__':
    process_bilibili_video("https://www.bilibili.com/video/BV1234567890", text_only=True)
```

## 配置说明

API 服务使用项目根目录下的 `config.py` 中的配置，可以通过修改配置文件或 `.env` 文件来调整行为：

- `MODEL_DIR`: 模型缓存目录（默认：`./models`）
- `OUTPUT_DIR`: 输出目录（默认：`./out`）
- `TEMP_DIR`: 临时文件目录（默认：`./temp`）
- `LLM_SERVER`: 默认 LLM 服务（默认：`deepseek-chat`）
- `LLM_TEMPERATURE`: LLM 温度参数（默认：`0.1`）
- `LLM_MAX_TOKENS`: LLM 最大 token 数（默认：`6000`）
- `ASR_MODEL`: ASR 模型（默认：`paraformer`）
- `WEB_SERVER_PORT`: Web 服务器端口（默认：`8000`）
- `TEXT_ONLY_DEFAULT`: （新增）Web UI 中 `仅返回文本(JSON)` 复选框的默认值，接受 `true` 或 `false`。将该键写入 `.env` 后，重启 Web UI 即可使配置生效。


## 注意事项

1. 任务是异步处理的，需要通过轮询 `/api/v1/task/{task_id}` 端点来获取处理状态。
2. 当前任务状态存储在内存中，服务重启后任务状态会丢失。生产环境建议使用 Redis 或数据库来存储任务状态。
3. 上传的临时文件会在处理完成后自动删除。
4. 当使用 `text_only=true` 时，系统不会生成 PDF/ZIP 等二进制产物 —— 仅返回文本字符串与处理元数据。
5. 建议设置文件上传大小限制，避免内存溢出。

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
