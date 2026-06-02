# TODO — AutoVoiceCollation v2.0

更新时间：2026-05-11

## 近期修复

- [x] **前端 checkbox 与标签文字间距过近** — 8 处 `gap-2` → `gap-3`（0.5rem → 0.75rem）

---

## 前端维护工具 ✅ 已完成

### 步骤 1：后端补齐 API（0.3 天）

- [x] 在 `history/manager.py` 加 `clear_all() -> int` 方法
- [x] 新增 `POST /api/v1/admin/clear-queue`
- [x] 新增 `POST /api/v1/admin/clear-history`
- [x] 新增 `POST /api/v1/admin/clean-temp`
- [x] 新增 `POST /api/v1/admin/clean-output`
- [x] 新增 `POST /api/v1/admin/clean-download`
- [x] 所有端点加确认参数 `confirm: bool = Form(False)`
- [x] 新增 `GET /api/v1/admin/stats` 统计端点

### 步骤 2：前端「维护」面板（0.4 天）

- [x] 在任务列表标签页底部加「维护工具」折叠区
- [x] 5 个操作按钮，显示实时统计数字
- [x] 点击弹出确认对话框
- [x] 执行后自动刷新统计和任务列表
- [x] 按钮执行中禁用（loading 状态 + 内联反馈消息）

### 步骤 3：安全加固（0.2 天）

- [x] 「清空输出目录」执行前确认路径在项目根目录下
- [x] 操作日志记录（logger.info）

---

## 项目定位

> **音视频 → 结构化知识的处理管道，通过 MCP 接入 AI Agent 生态。**

核心价值：中文音视频 → 结构化知识，做 Hermes Agent 生态中最好的音视频处理后端。

---

## MVP：AutoVoiceCollation × Hermes Agent 集成

### 阶段 0：验证 MCP 集成 ✅（已完成 — 2026-05-09）

- [x] 用 Hermes `config.yaml` 配置接入 AutoVoiceCollation MCP Server（stdio）
  - 配置文件：`~/.hermes/config.yaml` → `mcp_servers.avc`
  - 启动命令：`python3 -m src.mcp.server`（PYTHONPATH=/mnt/e/proj/AutoVoiceCollation）
  - `hermes mcp test avc` ✓ 5 个 Tool 全部发现
- [x] 在 Hermes CLI 中测试 `process_bilibili` tool，确认 task_id 返回
  - MCP 协议级验证通过：`initialize` → `tools/list` → `tools/call` 全链路
- [x] 测试 `get_task_status` 轮询，确认链路：提交 → 等待 → 获取结果
  - 5 个 Tool 全部注册：process_bilibili / process_audio / process_batch / get_task_status / cancel_task

### 阶段 1：结构化分析 Tool ✅ 已完成（2026-05-12）

- [x] 新增 `analyze_video(url)` MCP Tool — 一步完成"转写 + LLM 分析"
- [x] 定义 Pydantic 输出模型 `VideoAnalysis`（title/transcript/summary/key_points/segments）
- [x] 内部复用 inference_queue 提交任务 + 轮询完成
- [x] 完成后用 `SUMMARY_LLM_SERVER` 做摘要 + 关键点提取
- [x] 已上线验证：Hermes 调用成功返回 6 条 key_points + 3 个 segments
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

### B站搜索接口 ✅ 已完成（2026-05-15）

> **解锁搜索→分析流水线**：用户给主题，Agent 搜索视频 → 选择 → analyze_video → 聚合报告。

- [x] 新增 MCP Tool: `search_bilibili(keyword, max_results=10)` → `[{bvid, title, duration, play_count, description, author, url}]`
- [x] 调用 B站公开搜索 API（WBI 签名 + buvid3 cookie，无需登录）
- [x] 实现位置：`src/mcp/bilibili_api.py`（135 行，WBI 签名 + HTTpx 会话管理） + `src/mcp/server.py`（7 行，Tool 注册）
- [ ] 前端可选：搜索框 + 结果列表（P2，Agent 优先）

**工作原理**：
```
Hermes: "研究一下 AI Agent 的最新进展"
→ search_bilibili("AI Agent") → 返回 10 个视频
→ 用户/Agent 选 3 个
→ 逐个 analyze_video → 聚合摘要 → 研究报告
```

---

## 中期：输出结构化 + 分析层升级

### 思维导图生成 ✅ 已实现

> **从转写文本自动生成结构化思维导图，让视频内容一目了然。**

#### 已完成

- [x] `MindMapNode` / `MindMapOutput` Pydantic 递归树模型
- [x] `MINDMAP` prompt 注册（LLM 提取层级主题 → JSON）
- [x] Mermaid + JSON 渲染器（`render_mermaid` / `render_json`）
- [x] `OUTPUT_STYLE=mindmap` + text_exporter 分支
- [x] `POST /api/v1/task/{task_id}/mindmap` API 端点
- [x] MCP Tool: `generate_mindmap(task_id)`

#### 增强：多层级深度控制（0.5 天）

> **当前限制**：只支持 2 层（主题 → 子要点），无法生成更深层次的导图。

**步骤 1: 数据模型（0.1 天）**

- [ ] 新增 `MindMapDepth` 枚举：`low`（2层）/ `medium`（3层）/ `high`（4层）/ `auto`（模型自主）
- [ ] `MindMapOutput` 增加 `depth` 字段

**步骤 2: 动态 Prompt（0.15 天）**

- [ ] 根据 `depth` 动态构建 prompt：
  - `low`: "提取 3-5 个一级主题，每个下 2-4 个子要点"（当前行为）
  - `medium`: "提取 3-5 个一级主题 → 每个 2-3 个子主题 → 每个 2-3 个要点"
  - `high`: "提取 3-5 个一级分类 → 每个 2-3 个主题 → 每个 2-3 个子主题 → 每个 2-3 个要点"
  - `auto`: "根据内容复杂程度自行决定层级深度，长文本可深，短文本可浅"
- [ ] `generate_mindmap(text, title, depth="low")` 参数

**步骤 3: 前端 + API（0.15 天）**

- [ ] 前端「高级选项」增加深度下拉框：`低(2层) / 中(3层) / 高(4层) / 自动`
- [ ] API 端点增加 `depth` 参数
- [ ] MCP Tool 增加 `depth` 参数

**步骤 4: 验证（0.1 天）**

- [ ] 同一段文本用 4 种深度生成导图，对比层级和节点数
- [ ] `auto` 模式对长短文本的适应性验证

#### 不做

- ~~手绘风格导图~~ — 超出 MVP 范围，第三方库太重
- ~~实时协作编辑导图~~ — 非本项目定位
- ~~OCR 白板/手写导图识别~~ — 不同领域
- ~~Graphviz PNG 渲染~~ — Mermaid + JSON 已覆盖 Agent/Web 需求

---

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
- [x] MCP stdio Server — 6 个 Tool（含 generate_mindmap）
- [x] LLM 提供者重构 — 数据驱动注册表（新增模型只需 1 行）
- [x] DeepSeek V4 Pro / Flash 支持
- [x] ffmpeg 自动检测
- [x] Paraformer generate_with_timestamps 修复
- [x] PDF 中英文混排 — 去除双字体系统
- [x] 异步 LLM 调用 — aiohttp + asyncio.run
- [x] 段落分割保留 — split_text 不再吃掉换行
- [x] VAD 服务移植 — fsmn-vad 预处理（ENABLE_VAD=true）
- [x] 脚本清理 — 14 → 5
- [x] Hermes Agent 安装 + MCP 集成验证
- [x] subtitle/generator.py 解耦 — 拆为 7 个模块文件
- [x] 思维导图生成 — LLM 提取层级主题 + Mermaid/JSON 输出
- [x] 前端配置开关 — output_style / LLM润色 / LLM摘要 暴露到 Web UI
- [x] PDF 段落排版修复 — polish prompt 增加自然分段规则，消除整墙文字
- [x] Phase 1 analyze_video — 结构化分析 MCP Tool + VideoAnalysis 模型
- [x] MCP 架构重构 — 从嵌入式队列改为 HTTP 代理层（解决任务丢失问题）
- [x] MCP 完善 — get_task_status 直接返回文本 + 5 个 Resource（avc://task/{id}/...）
- [x] prompt_hint — Agent 通过 prompt_hint 参数控制 LLM 分析方向
- [x] Code Review 修复 — 超时、ruff 警告、死代码清理、pre-commit hook 跨平台
- [x] search_bilibili — B站视频搜索 MCP Tool（WBI 签名 + buvid3，无需登录）

---

## 处理管线优化（2026-05-24）

> **从实战踩坑中提炼：管线效率、分析深度、Agent 体验三个维度的改进。**

### P0: CC 字幕 Fast Path（0.5 天）

> **问题**：每条视频都 下载音频 → Whisper ASR，不论是否已有现成字幕。B站 AI 字幕覆盖率逐年提高，热门视频几乎都有 CC 字幕。

**步骤 1: CC 字幕探测（0.15 天）**

- [ ] 新增 `src/mcp/cc_subtitle.py`：调用 `x/player/v2` 的 `subtitle.subtitles` 字段
- [ ] 若存在 CC 字幕，下载 JSON → 提取纯文本
- [ ] 文本长度阈值判断（< 200 字视为无效，fallback 到 ASR）

**步骤 2: 管线集成（0.2 天）**

- [ ] `VideoProcessor.process()` — 下载音频前先尝试 CC 字幕
- [ ] `MultiPartVideoProcessor._process_single_part()` — 同样加 fast path
- [ ] CC 字幕命中时跳过 `download_bilibili_audio()` + `transcribe_audio()`，直接进入润色/分析
- [ ] 未命中时回退现有 ASR 流程，零影响

**步骤 3: 验证（0.15 天）**

- [ ] 有 CC 字幕的视频：对比 CC 路径 vs ASR 路径的结果质量 + 耗时
- [ ] 无 CC 字幕的视频：确认 fallback 正常工作
- [ ] 多P 视频（教程合集）：确认每个分P 独立判断 CC/ASR

**不做**：
- ~~用 CC 字幕完全替代 ASR~~ — 很多深度内容（技术分享、演讲）没有 CC 字幕

---

### P1: 队列健壮性（1 天）

> **问题（实战复现）**：`pending` 状态永不推进、取消后队列不解锁、无超时机制。

**步骤 1: 任务超时（0.3 天）**

- [ ] `InferenceQueue` 增加 `task_timeout` 配置（默认 10 分钟）
- [ ] `pending` 超时自动标记 `timeout`，释放队列槽位
- [ ] `processing` 超时自动标记 `failed`，释放 Worker

**步骤 2: 取消语义修正（0.2 天）**

- [ ] `cancel_task` 立即从队列移除（而非 "提交取消请求"）
- [ ] 正在 `processing` 的任务设置中断标志，Worker 下一轮检查时终止

**步骤 3: 可观测性（0.3 天）**

- [ ] `get_task_status` 返回 `queue_position`（在 pending 队列中的位置）
- [ ] Worker 心跳检测（30s 间隔），死 Worker 自动驱逐
- [ ] `GET /api/v1/admin/queue-status` 显示队列深度 + Worker 状态

**步骤 4: 验收（0.2 天）**

- [ ] 提交 3 个任务 → 验证 queue_position 正确递减
- [ ] 模拟 Worker 崩溃 → 验证超时自动重分配
- [ ] cancel 任务 → 验证队列立即释放

---

### P2: 元数据富化（0.5 天）

> **问题**：LLM 分析时只知道视频标题 + 转写文本。B站丰富的元数据（分P目录、热评、标签）未被利用。

**步骤 1: 元数据采集（0.2 天）**

- [ ] `src/mcp/bilibili_api.py` 新增 `get_video_metadata(bvid)` — 聚合以下数据：
  - 视频信息：`x/web-interface/view` → title/desc/tags/owner
  - 分P目录：`x/player/pagelist` → 章节列表
  - 热门评论：`x/v2/reply/main` → top 5 热评
- [ ] 结构化输出为 `VideoMetadata` Pydantic model

**步骤 2: 分析注入（0.2 天）**

- [ ] `VideoAnalysis` 入口调用 `get_video_metadata`，作为 system prompt 的一部分注入 LLM
- [ ] `analyze_video` MCP Tool 返回结果中包含原始 metadata
- [ ] `generate_analysis` 的 prompt 模板增加 metadata 占位符

**步骤 3: 验证（0.1 天）**

- [ ] 对比有无 metadata 的分析质量：key_points 相关性、segments 主题准确度
- [ ] 确认 API 超时不阻塞主流程（metadata 采集失败 → 降级到无 metadata 模式）

---

### P3: MCP 一键式 + 分析结构化（0.5 天）

> **问题 1**：Agent 调用 `process_bilibili` → 轮询 `get_task_status` 需要写循环，增加 token 消耗和复杂度。
> **问题 2**：`get_task_status` 把结构化分析结果摊平到 `text` 字段，丢失 key_points/segments 结构。

**步骤 1: 一键式阻塞等待（0.2 天）**

- [ ] `analyze_video` 内部改为：提交任务 → 轮询直到完成 → 直接返回结果
- [ ] 超时保护：最大等待 `task_timeout`，超时返回当前状态
- [ ] 保持 `process_bilibili` 的异步语义不变（向后兼容）

**步骤 2: 结构化输出保留（0.2 天）**

- [ ] `get_task_status` 返回 `analysis` 字段（包含 `summary` / `key_points` / `segments`），替代摊平的 `text` 字段
- [ ] MCP Resource `avc://task/{id}/analysis` 返回完整 `VideoAnalysis` JSON
- [ ] `generate_mindmap` 直接消费 `analysis.segments` 结构而非重新解析

**步骤 3: 验证（0.1 天）**

- [ ] Hermes Agent 调用 `analyze_video`：确认一次调用拿到完整结果（无需轮询）
- [ ] `get_task_status` 返回的 `analysis` 字段与原始 `VideoAnalysis` 一致

---

### P4: 多P 视频智能采样（0.3 天）

> **问题**：110 集的教程合集，强制全量下载+ASR = 不可行。

**步骤 1: 采样策略（0.15 天）**

- [ ] `MultiPartVideoProcessor` 新增参数 `part_sample`（None=全量 / int=N 随机采样）
- [ ] 新增策略 `head+middle+tail`：首中尾各取 M 个分P
- [ ] 新增策略 `cc_only`：仅处理有 CC 字幕的分P（搭配 CC Fast Path）

**步骤 2: API/MCP 暴露（0.1 天）**

- [ ] `POST /api/v1/process/bilibili` 增加 `part_sample` 参数
- [ ] MCP `process_bilibili` / `process_batch` 增加 `part_sample` 参数

**步骤 3: 验证（0.05 天）**

- [ ] 110 集教程 `part_sample=5`：确认只处理 5 个分P
- [ ] `cc_only` 模式：确认跳过无 CC 字幕的分P

---

## 不做

- ~~Qwen2.5-Omni GGUF 替代 ASR~~ — 精度和时间戳不如专用 ASR
- ~~独立 Worker 进程 + SQLite 持久化~~ — MVP 内存态足够
- ~~重写成通用 Agent~~ — Hermes 已有 13.7K 行核心循环，做好 MCP 后端即可
- ~~Audio-native LLM 替代 ASR~~ — CER 差距仍在 3x
- ~~Realtime API~~ — 不同市场（实时对话 vs 内容处理）
