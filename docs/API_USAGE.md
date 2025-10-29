# AutoVoiceCollation API 使用文档

## 简介

AutoVoiceCollation 提供了基于 FastAPI 的 HTTP 接口，方便与其他程序进行集成和交互。文档包含常用端点说明、参数与示例调用方式。

## 最新更新

### v1.1.0 - 文本总结功能

新增功能：

- ✨ **独立总结端点** `/api/v1/summarize`：直接对文本进行学术风格的总结
- ✨ **summarize 参数**：在处理端点中添加 `summarize` 参数，自动对处理结果生成总结
- 📝 总结采用学术小论文格式，包含引言、主体和结论
- 🔧 支持自定义 LLM 参数（temperature、max_tokens）以优化总结质量

使用场景：

- 快速总结长视频/音频的核心内容
- 生成学术研究笔记
- 批量处理并汇总多个视频的要点

## 启动 API 服务

```bash
# 方式1：直接运行
python api.py

# 方式2：使用 uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

访问 `http://localhost:8000/docs` 查看交互式 API 文档（Swagger UI）。

## 通用说明

- **text_only 参数**（布尔）：如果为 `true`，处理过程只返回纯文本结果（以及处理信息元数据），不会生成 PDF、ZIP 或其它文档格式的输出文件。
    - 默认行为：`text_only=false`（仍会生成 PDF、ZIP 等文件并在下载端点提供下载）。
    - 当使用 `text_only=true` 时：处理完成后，任务的 `result` 字段将包含文本内容与若干处理时长/路径信息；不会生成 zip 下载包。

- **summarize 参数**（布尔，新增）：如果为 `true`，系统会在处理完成后调用 LLM 对润色后的文本进行总结，生成学术风格的小论文摘要。
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
  "text_only": false,
  "summarize": false
}
```

字段说明：

- `video_url`：B 站视频完整链接（必需）
- `llm_api`：要使用的 LLM 服务（可选，默认：`deepseek-chat`）
- `temperature`：LLM 温度参数（可选，默认：`0.1`）
- `max_tokens`：生成文本时的最大 token 数（可选，默认：`6000`）
- `text_only`：是否只返回纯文本结果（可选，默认：`false`）
- `summarize`：是否生成文本总结（可选，默认：`false`，**需要配合 `text_only=true` 使用**）

响应示例（任务提交）：

```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "任务已提交，正在处理中"
}
```

示例 curl（不生成总结）：

```bash
curl -X POST "http://localhost:8000/api/v1/process/bilibili" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.bilibili.com/video/BV1wP411W7pe?t=0.3",
    "llm_api": "deepseek-chat",
    "temperature": 0.1,
    "max_tokens": 6000,
    "text_only": true
  }'
```

示例 curl（生成总结）：

```bash
curl -X POST "http://localhost:8000/api/v1/process/bilibili" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.bilibili.com/video/BV1wP411W7pe?t=0.3",
    "llm_api": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 4000,
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
- 其它参数：`llm_api`、`temperature`、`max_tokens`、`text_only`、`summarize` 通过 URL 查询参数传递（可选），例如：
  `?llm_api=deepseek-chat&temperature=0.1&max_tokens=6000&text_only=true&summarize=true`。

示例 curl（不生成总结）：

```bash
curl -X POST "http://localhost:8000/api/v1/process/audio?llm_api=deepseek-chat&temperature=0.1&max_tokens=6000&text_only=true" \
  -F "file=@/path/to/audio.mp3"
```

示例 curl（生成总结）：

```bash
curl -X POST "http://localhost:8000/api/v1/process/audio?llm_api=deepseek-chat&temperature=0.7&max_tokens=4000&text_only=true&summarize=true" \
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
  "text_only": false,
  "summarize": false
}
```

说明：

- `text_only` 和 `summarize` 可对整个批次统一控制（true/false）。
- 当 `summarize=true` 且 `text_only=true` 时，会对每个视频的文本分别生成总结。

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

字段说明：

- `text`：要总结的文本内容（必需）
- `title`：文本标题，用于总结时的上下文（可选，默认为空字符串）
- `llm_api`：要使用的 LLM 服务（可选，默认：`deepseek-chat`）
- `temperature`：LLM 温度参数（可选，默认：`0.1`）
- `max_tokens`：生成总结时的最大 token 数（可选，默认：`6000`）

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
    "text": "这里是一段很长的文本内容，需要进行学术性总结...",
    "title": "关于人工智能的思考",
    "llm_api": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 4000
  }'
```

注意：

- 此端点是**同步的**，不会创建后台任务，处理完成后直接返回结果。
- 适用于已有文本需要快速总结的场景。
- 如果需要对音视频内容进行处理并总结，请使用其他处理端点并设置 `summarize=true`。

---

### 8. 查询任务状态

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
    "polished_text": "这里是润色后的完整文本内容...",
    "audio_text": "这里是原始ASR提取的文本...",
    "title": "视频标题",
    "extract_time": 10.5,
    "polish_time": 5.2
  }
}
```

响应示例（`text_only=true` 且 `summarize=true` 的情况）：

```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "message": "处理完成",
  "result": {
    "polished_text": "这里是润色后的完整文本内容...",
    "audio_text": "这里是原始ASR提取的文本...",
    "title": "视频标题",
    "summary": "这里是LLM生成的学术风格总结，以小论文形式呈现...",
    "extract_time": 10.5,
    "polish_time": 5.2
  }
}
```

说明：

- 当 `text_only=false` 时，`result` 中包含 `output_dir` 和 `zip_file` 字段。
- 当 `text_only=true` 时，`result` 中包含 `polished_text`（润色后文本）、`audio_text`（原始文本）、`title`（标题）等字段。
- 当同时启用 `summarize=true` 时，`result` 中会额外添加 `summary` 字段，包含 LLM 生成的学术总结。

---

### 9. 下载处理结果

**GET** `/api/v1/download/{task_id}`

下载任务处理结果（ZIP 文件）。

示例：

```bash
curl -O -J http://localhost:8000/api/v1/download/your-task-id
```

说明：如果任务是使用 `text_only=true` 提交并且服务未生成 zip 包，则该下载端点可能返回 404 或空内容；请直接在 `/api/v1/task/{task_id}` 的 `result.text` 中获取纯文本结果。

## Web UI（`webui.py`）说明

- 在每个处理 Tab（例如 B 站、音频、批量）中已加入 `text_only` 和 `summarize` 复选框控件。
- **text_only**：勾选后，前端会在请求体/表单中传递 `text_only=true` 到后端，下游处理流程将只返回纯文本并跳过 PDF/ZIP 生成。
- **summarize**：勾选后，会在请求中传递 `summarize=true`，系统会对处理结果生成学术风格的总结。
    - **必须同时勾选 `text_only` 才能生效**。
    - 总结功能会增加处理时间（需要额外的 LLM 调用）。
- **字幕端点特殊说明**：字幕端点 `/api/v1/process/subtitle` 在当前后端实现中不读取 `text_only` 和 `summarize`
  参数，前端应避免对该端点传递这些参数。
- 如果需要下载文件（PDF/ZIP），请确保在 UI 中不勾选 `text_only`。

## Python 客户端示例

### 示例 1：处理 B站视频（带总结功能）

```python
import requests
import time

BASE_URL = "http://localhost:8000"

def process_bilibili_video(video_url, text_only=False, summarize=False):
    """
    处理 B站视频

    Args:
        video_url: B站视频链接
        text_only: 是否只返回文本结果
        summarize: 是否生成总结（需要 text_only=True）
    """
    # 提交任务
    response = requests.post(
        f"{BASE_URL}/api/v1/process/bilibili",
        json={
            "video_url": video_url,
            "llm_api": "deepseek-chat",
            "temperature": 0.7 if summarize else 0.1,
            "max_tokens": 4000 if summarize else 6000,
            "text_only": text_only,
            "summarize": summarize
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

            if text_only:
                # 获取润色后的文本
                polished_text = result.get("polished_text")
                if polished_text:
                    print(f"\n润色后的文本（前500字）:\n{polished_text[:500]}...\n")

                # 如果有总结，显示总结
                if summarize and "summary" in result:
                    summary = result["summary"]
                    print(f"\n学术总结:\n{summary}\n")

                # 显示其他信息
                print(f"标题: {result.get('title', 'N/A')}")
                print(f"提取时间: {result.get('extract_time', 0):.2f}秒")
                print(f"润色时间: {result.get('polish_time', 0):.2f}秒")
            else:
                # 非 text_only：返回文件路径
                zip_file = result.get("zip_file")
                if zip_file:
                    print(f"生成了 ZIP 文件：{zip_file}")
                    print("可以使用 /api/v1/download/{task_id} 下载")
            break

        elif status == "failed":
            print(f"处理失败: {status_data.get('message')}")
            break

        time.sleep(5)

# 使用示例
if __name__ == '__main__':
    # 示例1：只获取文本，不生成总结
    print("=== 示例1：获取文本（不生成总结）===")
    process_bilibili_video(
        "https://www.bilibili.com/video/BV1234567890",
        text_only=True,
        summarize=False
    )

    print("\n" + "="*50 + "\n")

    # 示例2：获取文本并生成总结
    print("=== 示例2：获取文本并生成总结 ===")
    process_bilibili_video(
        "https://www.bilibili.com/video/BV1234567890",
        text_only=True,
        summarize=True
    )
```

### 示例 2：直接总结文本

```python
import requests

BASE_URL = "http://localhost:8000"

def summarize_text(text, title=""):
    """
    直接对文本进行总结

    Args:
        text: 要总结的文本内容
        title: 文本标题（可选）

    Returns:
        总结结果字典
    """
    response = requests.post(
        f"{BASE_URL}/api/v1/summarize",
        json={
            "text": text,
            "title": title,
            "llm_api": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 4000
        }
    )
    response.raise_for_status()
    return response.json()

# 使用示例
if __name__ == '__main__':
    long_text = """
    这里是一段很长的文本内容，可能来自文档、网页或其他来源。
    系统会使用 LLM 对这段文本进行学术性总结...
    """ * 100  # 模拟长文本

    result = summarize_text(long_text, title="关于人工智能的探讨")

    print(f"原始文本长度: {result['original_length']} 字符")
    print(f"总结文本长度: {result['summary_length']} 字符")
    print(f"\n总结内容:\n{result['summary']}")
```

### 示例 3：批量处理并生成总结

```python
import requests
import time

BASE_URL = "http://localhost:8000"

def process_batch_with_summary(urls):
    """批量处理视频并生成总结"""
    response = requests.post(
        f"{BASE_URL}/api/v1/process/batch",
        json={
            "urls": urls,
            "llm_api": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 4000,
            "text_only": True,
            "summarize": True
        }
    )
    response.raise_for_status()
    task_id = response.json()["task_id"]
    print(f"批量任务已提交，ID: {task_id}")

    # 轮询任务状态
    while True:
        status_response = requests.get(f"{BASE_URL}/api/v1/task/{task_id}")
        status_response.raise_for_status()
        status_data = status_response.json()
        status = status_data["status"]

        if status == "completed":
            result = status_data["result"]
            summaries = result.get("summaries", [])

            print(f"\n处理完成！共生成 {len(summaries)} 个总结：")
            for i, item in enumerate(summaries, 1):
                print(f"\n--- 视频 {i}: {item.get('title', 'N/A')} ---")
                print(f"总结: {item.get('summary', 'N/A')[:200]}...")
            break

        elif status == "failed":
            print(f"处理失败: {status_data.get('message')}")
            break

        time.sleep(10)

# 使用示例
if __name__ == '__main__':
    urls = [
        "https://www.bilibili.com/video/BV1111111111",
        "https://www.bilibili.com/video/BV2222222222"
    ]
    process_batch_with_summary(urls)
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

1. **任务处理**：任务是异步处理的，需要通过轮询 `/api/v1/task/{task_id}` 端点来获取处理状态。
2. **任务状态存储**：当前任务状态存储在内存中，服务重启后任务状态会丢失。生产环境建议使用 Redis 或数据库来存储任务状态。
3. **临时文件**：上传的临时文件会在处理完成后自动删除。
4. **text_only 模式**：
    - 当使用 `text_only=true` 时，系统不会生成 PDF/ZIP 等二进制产物，仅返回文本字符串与处理元数据。
    - 如果需要持久化文件（例如 PDF），请把 `text_only` 设为 `false`（默认）。
5. **summarize 功能**：
    - `summarize` 参数**必须配合 `text_only=true` 使用**，否则不会生效。
    - 总结功能会额外调用一次 LLM API，会增加处理时间和成本。
    - 生成的总结采用学术风格的小论文格式，包含引言、主体和结论。
    - 建议使用较高的 `temperature`（如 0.7）和较大的 `max_tokens`（如 4000）以获得更好的总结质量。
6. **文件大小限制**：建议设置文件上传大小限制，避免内存溢出。
7. **并发限制**：生产环境建议配置并发处理数量限制，避免资源耗尽。

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
