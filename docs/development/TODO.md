# TODO — AutoVoiceCollation v2.0

更新时间：2026-05-08

## 项目定位

> **音视频 → 结构化知识的处理管道，通过 MCP 接入 AI Agent 生态。**

核心价值：中文音视频 → 结构化知识，做 Hermes Agent 生态中最好的音视频处理后端。

---

## MVP：AutoVoiceCollation × Hermes Agent 集成

### 阶段 0：验证 MCP 集成（1 天）

- [ ] 用 Hermes `mcp.json` 配置接入 AutoVoiceCollation MCP Server（stdio）
- [ ] 在 Hermes CLI 中测试 `process_bilibili` tool，确认 task_id 返回
- [ ] 测试 `get_task_status` 轮询，确认链路：提交 → 等待 → 获取结果

### 阶段 1：结构化分析 Tool（3 天）

- [ ] 新增 `analyze_video(url)` MCP Tool — 一步完成"转写 + LLM 分析"
- [ ] 定义 Pydantic 输出模型 `VideoAnalysis`：
  ```
  {
    "title": "...",
    "transcript": "完整转写文本",
    "summary": "200字摘要",
    "key_points": ["要点1", "要点2", ...],
    "segments": [{"start": 0, "end": 30, "text": "...", "topic": "..."}],
    "output_dir": "/path/to/output"
  }
  ```
- [ ] 内部复用 inference_queue 提交任务 + 轮询完成
- [ ] 完成后用 `SUMMARY_LLM_SERVER` 做摘要 + 关键点提取
- [ ] 添加 JSON Schema 输出验证

### 阶段 2：Hermes Skill 封装（1 天）

- [ ] 创建 Hermes Skill Document（agentskills.io 格式）
- [ ] Skill 定义 prompt template：摘要风格、要点数量、语言偏好
- [ ] 测试 Hermes 自主决策：收到 URL 后自动选择 `analyze_video`

### 阶段 3：频道监控 Cron（2 天）

- [ ] 新增 `check_channel(channel_url)` MCP Tool — 返回频道新视频列表
- [ ] 去重逻辑：通过 history manager 跳过已处理视频
- [ ] Hermes Cron 配置模板：定时 check + analyze 流水线

---

## 中期：输出结构化 + 分析层升级

### 结构化输出

- [ ] `OUTPUT_STYLE=json` 模式 — Agent 可消费的结构化输出
- [ ] MCP Resource：`avc://task/{id}/transcript`、`/polished`、`/summary`
- [ ] Pydantic 输出模型全覆盖（`TranscriptSegment`、`ProcessResult`）

### 分析层

- [ ] 关键点提取 — 不只"润色"，而是提取核心论点、关键术语、行动项
- [ ] 时间轴标注 — 每段文本标注 start_time → end_time
- [ ] 章节/主题分段 — LLM 分析全文结构，自动生成目录
- [ ] Speaker 标记 — 结合 VAD + 声纹特征做说话人分段（远期）

---

## 远期：摄入层扩展 + MCP 增强

### 多源摄入

- [ ] YouTube 支持 — `POST /api/v1/process/youtube`（复用 yt-dlp）
- [ ] RSS / 频道监控 — `POST /api/v1/process/channel`
- [ ] 文件夹监控 — watcher 模式，监控目录自动处理新增音频

### MCP 增强

- [ ] MCP Resource 完善：`task/{id}/segments`、`/keywords`、`/timeline`
- [ ] Streamable HTTP 传输 — 从 stdio 升级，挂载到 FastAPI（`/mcp` 端点）
- [ ] 进度通知 — `notifications/progress` 推送任务进度

---

## 已完成（v1.1.0 — 2026-05-08）

- [x] 字幕接口修复 — `POST /api/v1/subtitle/generate`（JSON）
- [x] 历史记录接入 — 7 个完成点 + `GET /api/v1/history`
- [x] MCP stdio Server — 5 个 Tool（process_bilibili/audio/batch, get_task_status, cancel_task）
- [x] LLM 提供者重构 — 数据驱动注册表（新增模型只需 1 行）
- [x] DeepSeek V4 Pro / Flash 支持
- [x] ffmpeg 自动检测
- [x] Paraformer generate_with_timestamps 修复
- [x] PDF 中英文混排 — 去除双字体系统
- [x] 异步 LLM 调用 — aiohttp + asyncio.run
- [x] 段落分割保留 — split_text 不再吃掉换行
- [x] VAD 服务移植 — fsmn-vad 预处理（ENABLE_VAD=true）
- [x] 脚本清理 — 14 → 5

---

## 不做

- ~~Qwen2.5-Omni GGUF 替代 ASR~~ — 精度和时间戳不如专用 ASR
- ~~独立 Worker 进程 + SQLite 持久化~~ — MVP 内存态足够
- ~~重写成通用 Agent~~ — Hermes 已有 13.7K 行核心循环，做好 MCP 后端即可
- ~~Audio-native LLM 替代 ASR~~ — CER 差距仍在 3x
- ~~Realtime API~~ — 不同市场（实时对话 vs 内容处理）
