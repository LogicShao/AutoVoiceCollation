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

## 不做

- ~~Qwen2.5-Omni GGUF 替代 ASR~~ — 精度和时间戳不如专用 ASR
- ~~独立 Worker 进程 + SQLite 持久化~~ — MVP 内存态足够
- ~~重写成通用 Agent~~ — Hermes 已有 13.7K 行核心循环，做好 MCP 后端即可
- ~~Audio-native LLM 替代 ASR~~ — CER 差距仍在 3x
- ~~Realtime API~~ — 不同市场（实时对话 vs 内容处理）
