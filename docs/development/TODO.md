# TODO — AutoVoiceCollation v2.0

更新时间：2026-05-09

## 近期修复

- [x] **前端 checkbox 与标签文字间距过近** — 8 处 `gap-2` → `gap-3`（0.5rem → 0.75rem）

---

## 前端维护工具：清空队列 / 历史 / 临时文件 / 输出文件（1 天）

> **背景**：后端已有清理函数（`TaskManager.clear_all()`、`clean_directory()`、`delete_record()`），
> 但全部缺少 API 端点，前端也没有操作入口。

### 现状盘点

| 操作 | 后端函数 | API 端点 | 前端按钮 |
|---|---|---|---|
| 清空任务队列 | `TaskManager.clear_all()` ✅ | ❌ | ❌ |
| 清空历史记录 | `delete_record()` 仅单条 ❌ | ❌ | ❌ |
| 清理 temp 目录 | `clean_directory()` ✅ | ❌ | ❌ |
| 清理 output 目录 | `clean_directory()` ✅ | ❌ | ❌ |
| 清理 download 目录 | `clean_directory()` ✅ | ❌ | ❌ |

### 步骤 1：后端补齐 API（0.3 天）

- [ ] 在 `history/manager.py` 加 `clear_all() -> int` 方法（清空全部历史，返回清除条数）
- [ ] 新增 `POST /api/v1/admin/clear-queue` — 取消所有任务 + 清空 `tasks = {}`，返回被清除的任务数
- [ ] 新增 `POST /api/v1/admin/clear-history` — 调用 `history_manager.clear_all()`，返回清除条数
- [ ] 新增 `POST /api/v1/admin/clean-temp` — 调用 `clean_directory(config.paths.temp_dir)`，返回清除文件数
- [ ] 新增 `POST /api/v1/admin/clean-output` — 调用 `clean_directory(config.paths.output_dir)`，返回清除文件数
- [ ] 新增 `POST /api/v1/admin/clean-download` — 调用 `clean_directory(config.paths.download_dir)`，返回清除文件数
- [ ] 所有端点加确认参数 `confirm: bool = Form(False)`，前端传 `confirm=true` 才真正执行

### 步骤 2：前端「维护」面板（0.4 天）

- [ ] 在任务列表标签页底部加「维护工具」折叠区（`<details>`）
- [ ] 四个操作按钮（每个按钮点击后弹出确认对话框）：
  ```
  ┌─ 维护工具 ──────────────────────────┐
  │                                       │
  │  📋 清空任务队列    [执行]   (3 个任务) │
  │  📝 清空历史记录    [执行]   (12 条记录) │
  │  🗑 清理临时文件    [执行]   (45 MB)    │
  │  📁 清理输出目录    [执行]   (120 MB)   │
  │  💾 清理下载缓存    [执行]   (80 MB)    │
  │                                       │
  └───────────────────────────────────────┘
  ```
- [ ] 每个按钮先 `GET` 查询统计（任务数/记录数/文件大小），显示在按钮旁
- [ ] 点击后弹出 `confirm("确定要清空 XXX？此操作不可恢复。")`
- [ ] 执行后刷新统计数字

### 步骤 3：安全加固（0.2 天）

- [ ] 「清空输出目录」执行前确认 output_dir 路径以项目根目录开头（防止误删系统文件）
- [ ] 操作日志记录（logger.info 写入谁在什么时候执行了什么操作）

### 不做的

- ~~定时自动清理~~ — 运维需求，cron 更适合
- ~~选择性删除（勾选删除）~~ — 增加复杂度，MVP 全清即可
- ~~用户权限控制~~ — 单用户本地工具，无需

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

### 思维导图生成（2 天）← 新增

> **从转写文本自动生成结构化思维导图，让视频内容一目了然。**

**定位**: 依赖阶段 1 的 `analyze_video` 产出（key_points + segments with topics），
作为新的输出形态叠加到现有 6 种格式之上。

#### 步骤 1: 数据模型（0.3 天）

- [ ] 定义 `MindMapNode` Pydantic 模型（递归树结构）：
  ```
  {
    "title": "根节点",
    "children": [
      {"title": "主题A", "children": [
        {"title": "要点1", "children": []},
        {"title": "要点2", "children": []}
      ]},
      {"title": "主题B", "children": [...]}
    ]
  }
  ```
- [ ] 定义 `MindMapOutput` 包装模型（含 metadata: source_url, generated_at, node_count）

#### 步骤 2: LLM 主题提取 Prompt（0.3 天）

- [ ] 编写 `mindmap_from_transcript` prompt 模板
  - 输入：完整转写文本 + 已有的 key_points/segments
  - 约束：3-5 个一级主题、每主题 2-4 个子要点、纯 JSON 输出
  - 验证：JSON Schema 校验 + 节点数合理性检查（不超过 30 个）
- [ ] 在 `src/services/llm/prompts.py` 注册 prompt

#### 步骤 3: 渲染器（0.6 天）

- [ ] **Mermaid 渲染器** — 生成 `mindmap` 语法文本，直接嵌入 Markdown 输出
  ```
  mindmap
    root((视频标题))
      主题A
        要点1
        要点2
      主题B
        要点3
        要点4
  ```
- [ ] **Graphviz 渲染器** — 生成 PNG/SVG 图片，可嵌入 PDF 或独立输出
  - 依赖：`graphviz` Python 库（`pip install graphviz` + 系统安装 graphviz）
  - 节点颜色按层级区分、自动布局
- [ ] **JSON 树渲染器** — 直接输出 `MindMapOutput.model_dump_json()`，供 Agent/MCP 消费

#### 步骤 4: 接入输出管道（0.4 天）

- [ ] 新增 `OUTPUT_STYLE=mindmap` 配置选项
- [ ] 在 `text_exporter.py` 添加 `export_mindmap()` 分支
- [ ] 默认输出：`{output_dir}/mindmap.md`（Mermaid）+ `mindmap.json`（JSON）
- [ ] 可选：`mindmap.png`（需 graphviz）

#### 步骤 5: API + MCP（0.4 天）

- [ ] `POST /api/v1/task/{task_id}/mindmap` — 为已完成任务生成导图
- [ ] MCP Tool: `generate_mindmap(task_id)` — 返回 mindmap JSON + 文件路径
- [ ] MCP Resource: `avc://task/{id}/mindmap` — 结构化导图数据
- [ ] 作为 `analyze_video` 的可选输出（`include_mindmap=true`）

#### 不做的

- ~~手绘风格导图~~ — 超出 MVP 范围，第三方库太重
- ~~实时协作编辑导图~~ — 非本项目定位
- ~~OCR 白板/手写导图识别~~ — 不同领域

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

---

## 不做

- ~~Qwen2.5-Omni GGUF 替代 ASR~~ — 精度和时间戳不如专用 ASR
- ~~独立 Worker 进程 + SQLite 持久化~~ — MVP 内存态足够
- ~~重写成通用 Agent~~ — Hermes 已有 13.7K 行核心循环，做好 MCP 后端即可
- ~~Audio-native LLM 替代 ASR~~ — CER 差距仍在 3x
- ~~Realtime API~~ — 不同市场（实时对话 vs 内容处理）
