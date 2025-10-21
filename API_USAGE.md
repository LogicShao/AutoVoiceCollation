# AutoVoiceCollation API 使用文档

## 简介

AutoVoiceCollation 提供了 FastAPI 接口，方便与其他程序进行集成和交互。

## 启动 API 服务

```bash
# 方式1：直接运行
python api.py

# 方式2：使用 uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

访问 `http://localhost:8000/docs` 查看交互式 API 文档（Swagger UI）

## API 端点

### 1. 健康检查

**GET** `/health`

检查服务运行状态

```bash
curl http://localhost:8000/health
```

### 2. 处理 B 站视频

**POST** `/api/v1/process/bilibili`

提交 B 站视频处理任务

**请求体：**
```json
{
  "video_url": "https://www.bilibili.com/video/BV1...",
  "llm_api": "deepseek",
  "temperature": 0.1,
  "max_tokens": 6000
}
```

**响应：**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "任务已提交，正在处理中"
}
```

**示例：**
```bash
curl -X POST "http://localhost:8000/api/v1/process/bilibili" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.bilibili.com/video/BV1234567890",
    "llm_api": "deepseek",
    "temperature": 0.1,
    "max_tokens": 6000
  }'
```

### 3. 处理音频文件

**POST** `/api/v1/process/audio`

上传并处理音频文件

**表单数据：**
- `file`: 音频文件（支持 mp3, wav, m4a, flac）
- `llm_api`: LLM 服务（默认：deepseek）
- `temperature`: 温度参数（默认：0.1）
- `max_tokens`: 最大 token 数（默认：6000）

**示例：**
```bash
curl -X POST "http://localhost:8000/api/v1/process/audio" \
  -F "file=@/path/to/audio.mp3" \
  -F "llm_api=deepseek" \
  -F "temperature=0.1" \
  -F "max_tokens=6000"
```

### 4. 批量处理视频

**POST** `/api/v1/process/batch`

批量处理多个 B 站视频

**请求体：**
```json
{
  "urls": [
    "https://www.bilibili.com/video/BV1...",
    "https://www.bilibili.com/video/BV2..."
  ],
  "llm_api": "deepseek",
  "temperature": 0.1,
  "max_tokens": 6000
}
```

### 5. 生成视频字幕

**POST** `/api/v1/process/subtitle`

为视频生成字幕并硬编码

**表单数据：**
- `file`: 视频文件（支持 mp4, avi, mkv, mov）

**示例：**
```bash
curl -X POST "http://localhost:8000/api/v1/process/subtitle" \
  -F "file=@/path/to/video.mp4"
```

### 6. 查询任务状态

**GET** `/api/v1/task/{task_id}`

查询任务处理状态

**示例：**
```bash
curl http://localhost:8000/api/v1/task/your-task-id
```

**响应：**
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

任务状态：
- `pending`: 等待处理
- `processing`: 正在处理
- `completed`: 处理完成
- `failed`: 处理失败

### 7. 下载处理结果

**GET** `/api/v1/download/{task_id}`

下载任务处理结果（ZIP 文件）

**示例：**
```bash
curl -O -J http://localhost:8000/api/v1/download/your-task-id
```

## Python 客户端示例

```python
import requests
import time

# API 基础地址
BASE_URL = "http://localhost:8000"

def process_bilibili_video(video_url):
    """处理 B 站视频"""
    # 提交任务
    response = requests.post(
        f"{BASE_URL}/api/v1/process/bilibili",
        json={
            "video_url": video_url,
            "llm_api": "deepseek",
            "temperature": 0.1,
            "max_tokens": 6000
        }
    )
    task_id = response.json()["task_id"]
    print(f"任务已提交，ID: {task_id}")
    
    # 轮询任务状态
    while True:
        status_response = requests.get(f"{BASE_URL}/api/v1/task/{task_id}")
        status_data = status_response.json()
        status = status_data["status"]
        print(f"任务状态: {status} - {status_data['message']}")
        
        if status == "completed":
            print("处理完成！")
            print(f"结果: {status_data['result']}")
            
            # 下载结果
            download_response = requests.get(
                f"{BASE_URL}/api/v1/download/{task_id}",
                stream=True
            )
            with open("result.zip", "wb") as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("结果已下载到 result.zip")
            break
        elif status == "failed":
            print(f"处理失败: {status_data['message']}")
            break
        
        time.sleep(5)  # 每 5 秒查询一次

# 使用示例
process_bilibili_video("https://www.bilibili.com/video/BV1234567890")
```

## 配置说明

API 服务使用 `src/config.py` 中的配置，可以通过修改配置文件来调整行为：

- `MODEL_DIR`: 模型缓存目录（默认：`./models`）
- `OUTPUT_DIR`: 输出目录（默认：`./out`）
- `TEMP_DIR`: 临时文件目录（默认：`./temp`）
- `LLM_SERVER`: 默认 LLM 服务（默认：`deepseek`）
- `ASR_MODEL`: ASR 模型（默认：`paraformer`）

## 注意事项

1. 任务是异步处理的，需要通过轮询 `/api/v1/task/{task_id}` 端点来获取处理状态
2. 当前任务状态存储在内存中，服务重启后任务状态会丢失
3. 生产环境建议使用 Redis 或数据库来存储任务状态
4. 上传的临时文件会在处理完成后自动删除
5. 建议设置文件上传大小限制，避免内存溢出

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
