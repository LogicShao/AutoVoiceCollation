# API 使用指南（MVP）

## 1. 服务启动

```bash
python "api.py"
```

默认地址：

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

## 2. 调用模型

本项目主要处理类接口均采用“异步提交 + 轮询状态”模式：

1. 调用处理接口，立即返回 `task_id`
2. 轮询 `GET /api/v1/task/{task_id}` 获取状态
3. 完成后从 `result` 读取结果，或下载 ZIP

任务状态常见值：`pending`、`processing`、`completed`、`failed`、`cancelled`

注意：任务状态保存在内存中，服务重启后会丢失。

## 3. 端点总览

- `GET /`：返回 Web 页面（若前端文件存在）
- `GET /api`：API 信息
- `GET /health`：健康检查
- `POST /api/v1/process/bilibili`：处理 B 站视频
- `POST /api/v1/bilibili/check-multipart`：检测多 P 视频
- `POST /api/v1/process/multipart`：处理多 P 指定分段
- `POST /api/v1/process/audio`：上传音频/视频并处理
- `POST /api/v1/process/batch`：批量处理 B 站视频
- `POST /api/v1/process/subtitle`：为视频生成字幕
- `POST /api/v1/summarize`：纯文本摘要
- `GET /api/v1/task/{task_id}`：查询任务状态
- `GET /api/v1/tasks`：查询任务列表
- `POST /api/v1/task/{task_id}/cancel`：取消任务
- `GET /api/v1/download/{task_id}`：下载结果 ZIP

## 4. 处理类接口

### 4.1 处理单个 B 站视频

`POST /api/v1/process/bilibili`  
Content-Type: `application/json`

请求体：

```json
{
  "video_url": "https://www.bilibili.com/video/BV...",
  "llm_api": "Cerebras:Qwen-3-235B-Instruct",
  "temperature": 0.1,
  "max_tokens": 6000,
  "text_only": false,
  "summarize": false
}
```

### 4.2 检测是否为多 P 视频

`POST /api/v1/bilibili/check-multipart`  
Content-Type: `application/json`

```json
{
  "video_url": "https://www.bilibili.com/video/BV...",
  "llm_api": "Cerebras:Qwen-3-235B-Instruct",
  "temperature": 0.1,
  "max_tokens": 6000,
  "text_only": false,
  "summarize": false
}
```

返回示例（多 P）：

```json
{
  "is_multipart": true,
  "info": {
    "main_title": "示例标题",
    "total_parts": 3,
    "parts": [
      {
        "part_number": 1,
        "title": "P1",
        "duration": 120,
        "url": "https://..."
      }
    ]
  }
}
```

### 4.3 处理多 P 视频

`POST /api/v1/process/multipart`  
Content-Type: `application/json`

```json
{
  "video_url": "https://www.bilibili.com/video/BV...",
  "selected_parts": [1, 3],
  "llm_api": "Cerebras:Qwen-3-235B-Instruct",
  "temperature": 0.1,
  "max_tokens": 6000,
  "text_only": false
}
```

### 4.4 批量处理 B 站视频

`POST /api/v1/process/batch`  
Content-Type: `application/json`

```json
{
  "urls": [
    "https://www.bilibili.com/video/BVxxx",
    "https://www.bilibili.com/video/BVyyy"
  ],
  "llm_api": "Cerebras:Qwen-3-235B-Instruct",
  "temperature": 0.1,
  "max_tokens": 6000,
  "text_only": false,
  "summarize": false
}
```

### 4.5 上传音频/视频处理

`POST /api/v1/process/audio`  
Content-Type: `multipart/form-data`

表单字段：

- `file`：必填，支持音频和视频
- `llm_api`：可选
- `temperature`：可选
- `max_tokens`：可选
- `text_only`：可选，默认 `false`
- `summarize`：可选，默认 `false`

支持格式：

- 音频：`.mp3`、`.wav`、`.m4a`、`.flac`
- 视频：`.mp4`、`.avi`、`.mkv`、`.mov`、`.webm`、`.flv`

### 4.6 视频字幕生成

`POST /api/v1/process/subtitle`  
Content-Type: `multipart/form-data`

表单字段：

- `file`：必填，支持 `.mp4`、`.avi`、`.mkv`、`.mov`

## 5. 文本摘要接口

`POST /api/v1/summarize`  
Content-Type: `application/json`

```json
{
  "text": "待摘要文本",
  "title": "可选标题",
  "llm_api": "Cerebras:Qwen-3-235B-Instruct",
  "temperature": 0.1,
  "max_tokens": 6000
}
```

## 6. 任务查询与下载

### 6.1 查询任务状态

`GET /api/v1/task/{task_id}`

成功响应示例：

```json
{
  "task_id": "uuid",
  "status": "completed",
  "message": "处理完成",
  "result": {
    "output_dir": "out/xxx",
    "extract_time": 12.3,
    "polish_time": 5.6,
    "zip_file": "temp/xxx.zip"
  },
  "error": null,
  "created_at": "2026-02-10T10:00:00",
  "completed_at": "2026-02-10T10:01:00",
  "url": "https://www.bilibili.com/video/BV...",
  "filename": null
}
```

### 6.2 查询任务列表

`GET /api/v1/tasks`

### 6.3 取消任务

`POST /api/v1/task/{task_id}/cancel`

### 6.4 下载结果

`GET /api/v1/download/{task_id}`

当任务完成后，接口返回 ZIP 文件；若 `result.zip_file` 不存在，服务会基于 `output_dir` 进行懒打包。

## 7. cURL 快速示例

```bash
# 提交 B 站任务
curl -X POST "http://127.0.0.1:8000/api/v1/process/bilibili" \
  -H "Content-Type: application/json" \
  -d '{"video_url":"https://www.bilibili.com/video/BV...","text_only":false,"summarize":false}'

# 查询状态
curl "http://127.0.0.1:8000/api/v1/task/<task_id>"

# 下载结果
curl -L "http://127.0.0.1:8000/api/v1/download/<task_id>" -o result.zip
```
