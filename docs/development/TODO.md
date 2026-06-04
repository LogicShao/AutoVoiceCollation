# TODO — AutoVoiceCollation v2.0

更新时间：2026-06-04

> 本文件只保留未完成、待复核和明确不做的事项。已完成的历史明细不再在 TODO 中展开；需要追溯时查看 Git history。

## 项目定位

音视频 -> 结构化知识的处理管道，通过 MCP 接入 AI Agent 生态。

核心价值：中文音视频 -> 结构化知识，作为 Hermes Agent 生态中的音视频处理后端。

---

## 当前 P0：生产质量收尾

> 背景：生产质量提升已完成并提交，但 review 发现两个边界问题仍应收口，避免质量状态和短文本门控在特殊路径下失真。

- [x] 修复 `text_only + summarize` 路径只按 `polished_text` 门控的问题：摘要前同时检查原始 `audio_text`，避免短转写被润色扩写后仍进入 LLM 摘要。
- [x] 修复 `scan_output_cache()` 过度信任旧 `result.json.status` 的问题：对非 `failed` 状态按实际产物重新推断 `partial/completed`。
- [x] 为上述两个边界补充回归测试，覆盖短原文长润色、旧 `result.json` 与实际文件不一致两类情况。
- [x] 跑通 `ruff check .` 与 `pytest tests/test_quality_*.py -q`。

---

## 当前 P1：队列与任务状态收尾

> 背景：队列健壮性已有实现痕迹（`task_timeout`、心跳、队列位置计算），但 TODO 与实际 API 契约未完全同步。

- [x] 确认 `pending` 超时、`processing` 取消、中断标志释放 Worker 的实际行为，并补齐缺失测试：`processing` 取消保留 stop flag，`pending` 取消标记后由 Worker 跳过并释放提交时间。
- [x] 保留并对外暴露 `GET /api/v1/admin/queue-status`，接入 `InferenceQueue.get_queue_status()`。
- [x] 在任务查询响应中暴露 `queue_position`，更新 `TaskResponse` 与前端任务状态展示。
- [x] 验证取消 pending 任务后队列不会继续执行该任务，覆盖 Worker 跳过已取消任务的回归测试。

---

## 当前 P2：Agent 输出契约收尾

> 背景：MCP 的 `analysis` Resource、结构化分析和 B 站元数据注入已有实现，但外部契约仍需收敛。

- [x] 为 `VideoAnalysis` 增加 JSON Schema/契约验证，覆盖 `summary`、`key_points`、`segments`，并保留可选 `metadata` 字段。
- [x] `analyze_video` 返回结果包含原始 `metadata`：API 任务结果、MCP tool 与 `analysis` Resource 统一暴露，避免内部已采集但外部不可用。
- [x] 明确 `OUTPUT_STYLE=json` 是普通文本导出 JSON；Agent 可消费的分析 JSON 通过 `analyze_video`、`get_task_status.analysis` 或 `avc://task/{task_id}/analysis` 获取。
- [x] 统一 MCP Resource 列表与 README 文档：`transcript`、`polished`、`summary`、`mindmap`、`analysis`。
- [x] `generate_mindmap` 优先消费 `analysis.segments`，无结构化分段时再回退到转写/润色文本。

---

## 当前 P3：CC / 多P路径复核

> 背景：CC 字幕 Fast Path、多P采样、元数据富化等旧 P0-P4 中已有大量实现痕迹，但原 TODO 仍是未勾选状态。这里先保留复核项，而不是重复实现。

- [x] 复核 CC 字幕 Fast Path：有 CC、无 CC、短 CC、多语言字幕、多P 分页 CID 五类场景已有回归覆盖，均会在不可用时 fallback。
- [x] 对比 CC 路径与 ASR 路径的质量和耗时：默认启用合理，CC 命中时跳过下载/ASR 成本；短文本、无字幕、非中文字幕和 CID 缺失均回退 ASR。
- [x] 复核 `part_sample` 的 API/MCP 暴露：`multipart` 保留接入，`process_bilibili` / `process_batch` 的无效 MCP 参数已移除。
- [x] 复核 `cc_only` 采样策略：无 CC 分P 会被过滤；全部过滤为空时返回“所选视频的所有分P均无CC字幕，请尝试其他采样策略”。

---

## Backlog

### Hermes / Agent 集成

- [ ] 创建 Hermes Skill Document（agentskills.io 格式）。
- [ ] Skill 定义 prompt template：摘要风格、要点数量、语言偏好。
- [ ] 测试 Hermes 自主决策：收到 URL 后自动选择 `analyze_video`。
- [ ] 新增 `check_channel(channel_url)` MCP Tool，返回频道新视频列表。
- [ ] 频道监控去重：通过 history manager 跳过已处理视频。
- [ ] Hermes Cron 配置模板：定时 check + analyze 流水线。

### 搜索与前端

- [ ] B站搜索前端入口：搜索框 + 结果列表（P2，Agent 优先）。

### 思维导图

- [ ] 新增 `MindMapDepth` 枚举：`low` / `medium` / `high` / `auto`。
- [ ] `MindMapOutput` 增加 `depth` 字段。
- [ ] 根据 `depth` 动态构建 mindmap prompt。
- [ ] `generate_mindmap(text, title, depth="low")` 增加参数。
- [ ] API 端点与 MCP Tool 增加 `depth` 参数。
- [ ] 前端高级选项增加深度下拉框。
- [ ] 同一段文本用 4 种深度生成导图，对比层级和节点数。

### 分析层增强

- [ ] 时间轴标注：每段文本标注 `start_time -> end_time`。
- [ ] 章节/主题分段：LLM 分析全文结构，自动生成目录。
- [ ] Speaker 标记：结合 VAD + 声纹特征做说话人分段（远期）。

### 摄入层扩展

- [ ] YouTube 支持：`POST /api/v1/process/youtube`（复用 yt-dlp）。
- [ ] RSS / 频道监控：`POST /api/v1/process/channel`。
- [ ] 文件夹监控：watcher 模式，监控目录自动处理新增音频。

### MCP 增强

- [ ] MCP Resource 完善：`task/{id}/segments`、`/keywords`、`/timeline`。
- [ ] Streamable HTTP 传输：从 stdio 升级，挂载到 FastAPI（`/mcp` 端点）。
- [ ] 进度通知：`notifications/progress` 推送任务进度。

---

## 待从 TODO 移除的已完成历史

以下内容已从主 TODO 明细中移除，只保留本索引防止重复规划：

- 生产质量提升：生产级摘要、短文本门控、输出状态、缓存 dry-run、质量样本测试。
- 前端维护工具：后台维护面板、清理接口、统计接口。
- v1.1.0 已完成清单：字幕接口、历史记录、MCP stdio、LLM provider、DeepSeek、ffmpeg、VAD、思维导图、prompt_hint、B站搜索等。
- 近期小修复：前端 checkbox 与标签文字间距。

---

## 不做

- ~~Qwen2.5-Omni GGUF 替代 ASR~~ — 精度和时间成本不如专用 ASR。
- ~~独立 Worker 进程 + SQLite 持久化~~ — 当前阶段内存态足够，先把 API 契约与任务状态收敛。
- ~~重写成通用 Agent~~ — Hermes 已有 Agent 框架，本项目做好 MCP 后端即可。
- ~~Audio-native LLM 替代 ASR~~ — CER 差距仍明显。
- ~~Realtime API~~ — 实时对话与内容处理是不同产品方向。
- ~~手绘风格导图~~ — 超出 MVP 范围，第三方库太重。
- ~~实时协作编辑导图~~ — 非本项目定位。
- ~~OCR 白板/手写导图识别~~ — 不同领域。
