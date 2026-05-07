# 下一位 Agent 交接文档

更新时间：2026-05-06

## 1. 目的

本文档用于帮助下一位 Agent 在 `main` 主线基础上继续开发，避免重复判断仓库状态、误用 `dev` 分支、或在未澄清现状的情况下直接扩展新能力。

本文档结论基于当前仓库只读检查，不包含任何未验证的主观设想。

## 2. 当前开发基线

- 当前开发基线是 `main`。
- 当前工作区在交接时为干净状态，无未提交改动。
- `main` 最近一次提交是 `cf30b6c`，日期为 `2026-03-17`。
- `main` 在 `2026-03-17` 还有一次更早提交 `cb8a3da`，主要处理异步任务响应、文件名清洗和错误处理。
- `dev` 不是正在持续推进的新功能分支。`dev` 相对 `main` 只多 1 个提交：`4d350c1`，日期为 `2026-02-06`，主题是 `main.py` 重命名为 `main_cli.py` 并更新相关文档。

结论：

- `main` 是唯一可信开发基线。
- `dev` 只能作为历史提案、旧实现和旧文档的参考来源，不能直接视为待合并功能池。

## 3. 当前项目阶段判断

项目已不是方案期，而是：

- `MVP` 已成型。
- 主流程基本可用。
- 最近停留在稳定性收尾和测试补全阶段。

已经确认存在的主线能力：

- FastAPI API 服务，包含 B 站处理、本地音频处理、批量处理、分 P 处理、字幕处理、任务查询、任务列表、任务取消、结果下载。
- 异步推理队列，避免主请求阻塞。
- Web 前端基础界面，包含任务页和下载入口。
- CLI 入口。
- 多 ASR / LLM / 导出格式支持。
- 单元测试已覆盖 API、队列、文件名清洗、历史记录模块。

## 4. 已确认的关键事实

### 4.1 API 已落地

关键端点在 [api.py](E:/proj/AutoVoiceCollation/api.py)：

- [api.py#L356](E:/proj/AutoVoiceCollation/api.py#L356) `POST /api/v1/process/bilibili`
- [api.py#L524](E:/proj/AutoVoiceCollation/api.py#L524) `POST /api/v1/process/multipart`
- [api.py#L567](E:/proj/AutoVoiceCollation/api.py#L567) `POST /api/v1/process/audio`
- [api.py#L676](E:/proj/AutoVoiceCollation/api.py#L676) `POST /api/v1/process/batch`
- [api.py#L724](E:/proj/AutoVoiceCollation/api.py#L724) `POST /api/v1/process/subtitle`
- [api.py#L800](E:/proj/AutoVoiceCollation/api.py#L800) `GET /api/v1/task/{task_id}`
- [api.py#L808](E:/proj/AutoVoiceCollation/api.py#L808) `GET /api/v1/tasks`
- [api.py#L820](E:/proj/AutoVoiceCollation/api.py#L820) `POST /api/v1/task/{task_id}/cancel`
- [api.py#L859](E:/proj/AutoVoiceCollation/api.py#L859) `GET /api/v1/download/{task_id}`

### 4.2 任务系统仍是内存态

- 任务状态仍保存在 [api.py#L163](E:/proj/AutoVoiceCollation/api.py#L163) 的 `tasks = {}` 中。

影响：

- 服务重启后任务状态会丢失。
- 当前实现适合单进程、单机 `MVP`，不应误判为持久化任务系统。

### 4.3 异步推理队列已存在

- 异步队列实现位于 [src/api/inference_queue.py](E:/proj/AutoVoiceCollation/src/api/inference_queue.py)。

这意味着：

- 后续扩展能力时，应优先复用现有队列和 `task_id` 机制。
- 不应再平行创建第二套长任务调度链路。

### 4.4 Web 前端不是空壳

- 任务页在 [frontend/src/index.html#L279](E:/proj/AutoVoiceCollation/frontend/src/index.html#L279)。
- 下载入口在 [frontend/src/index.html#L342](E:/proj/AutoVoiceCollation/frontend/src/index.html#L342) 和 [frontend/src/index.html#L412](E:/proj/AutoVoiceCollation/frontend/src/index.html#L412)。

### 4.5 历史记录模块已完成实现和测试

关键定义位于 [src/core/history/manager.py#L44](E:/proj/AutoVoiceCollation/src/core/history/manager.py#L44)：

- [src/core/history/manager.py#L221](E:/proj/AutoVoiceCollation/src/core/history/manager.py#L221) `create_record_from_bilibili`
- [src/core/history/manager.py#L263](E:/proj/AutoVoiceCollation/src/core/history/manager.py#L263) `create_record_from_local_file`
- [src/core/history/manager.py#L303](E:/proj/AutoVoiceCollation/src/core/history/manager.py#L303) `get_statistics`
- [src/core/history/manager.py#L320](E:/proj/AutoVoiceCollation/src/core/history/manager.py#L320) `get_history_manager`

当前判断：

- 历史记录模块本身已具备实现和测试。
- 但在 `api.py`、`src/core/processors/`、`src/services/` 中未发现明确接入点。
- 在未再次核对前，不应假设“历史记录已接入主流程”。

## 5. 已知断点和待修问题

### 5.1 字幕前后端接口不一致

- 前端当前调用 [frontend/src/js/main.js#L318](E:/proj/AutoVoiceCollation/frontend/src/js/main.js#L318) 的 `/api/v1/subtitle/generate`
- 后端当前提供 [api.py#L724](E:/proj/AutoVoiceCollation/api.py#L724) 的 `/api/v1/process/subtitle`

而且：

- 前端使用 JSON 请求体。
- 后端当前接口是 `UploadFile` 文件上传模式。

这是一处明确的主线断点，应优先处理。

### 5.2 仍存在少量显式 TODO

- [src/text_arrangement/polish_by_llm.py#L127](E:/proj/AutoVoiceCollation/src/text_arrangement/polish_by_llm.py#L127) 改进异步调用
- [src/text_arrangement/text_exporter.py#L458](E:/proj/AutoVoiceCollation/src/text_arrangement/text_exporter.py#L458) 修复 PDF 中英文混排问题

### 5.3 `dev` 中存在大量旧文档和旧模块，不应整体回流

`main..dev` 差异包含但不限于：

- 旧提案文档恢复
- `main_cli.py`
- `src/core/database.py`
- `src/services/llm_service.py`
- `src/services/vad_service.py`
- `src/worker.py`

这类内容的风险在于：

- 无法保证与当前 `main` 的收敛方向一致
- 可能把已移除、已简化或已替代的实现重新带回主线

## 6. 对当前开发计划的审核结论

原计划：

1. 将 `dev` 分支中的计划功能作为一个实验选项
2. 开发 MCP 服务

审核结果：

- 第 1 点方向可保留，但表述必须收紧。
- 第 2 点方向成立，但必须拆阶段，不能直接将 MCP 深度耦合进现有主线而不做边界设计。

建议改写为：

1. 将 `dev` 视为历史提案和备选实现参考，不直接合并。仅筛选少量、可验证、与 `main` 兼容的点，作为实验功能或 feature flag 候选。
2. 在修复 `main` 已知断点后，基于现有处理链路开发 MCP `MVP`，先做 `stdio`，后评估 `Streamable HTTP`。

## 7. 关于 `dev` 分支的明确策略

允许做的事：

- 把 `dev` 里的提案文档作为思路输入
- 从 `dev` 中摘取单个、边界清晰、与当前 `main` 一致的小改动
- 用 `dev` 对照当前主线，理解历史收敛过程

不要做的事：

- 不要直接合并 `dev`
- 不要把 `dev` 里的整批文档、旧模块、旧命名整体恢复到 `main`
- 不要假设 `dev` 比 `main` 更新

如果必须复用 `dev` 内容，建议流程：

1. 先在 `main` 上明确当前问题。
2. 只提取最小必要片段。
3. 单独验证该片段是否仍与当前主线兼容。
4. 通过 feature flag 或独立模块接入，而不是直接覆盖现有实现。

## 8. MCP 服务建议路线

### 8.1 总体原则

- 优先复用现有 API 处理链路和异步队列。
- 不要复制一套新的“下载、转录、轮询、导出”逻辑。
- MCP 层只做协议适配和能力映射。

### 8.2 推荐推进顺序

第一阶段：

- 修主线断点
- 统一字幕前后端契约
- 再确认历史记录模块是否需要接入主流程

第二阶段：

- 做 `stdio` MCP Server `MVP`
- 先服务本地 Agent / IDE / Desktop Host 集成场景

第三阶段：

- 视需要再做 `Streamable HTTP`
- 如果挂到现有 FastAPI 或 ASGI 服务中，必须补充安全边界

### 8.3 推荐的 MCP MVP 能力范围

优先做 Tool：

- `process_bilibili`
- `process_audio`
- `process_batch`
- `get_task_status`
- `cancel_task`

后续可做 Resource：

- `task transcript`
- `task polished_text`
- `task summary`
- `task output metadata`

不建议在第一版做的事：

- 直接传超大音视频二进制
- 新建独立持久化任务系统
- 在 MCP 层重写现有业务逻辑

### 8.4 推荐实现方式

建议新增独立入口，例如：

- `src/mcp/server.py`

推荐结构：

- MCP 层只负责参数校验、Tool/Resource 注册、结果映射
- 业务处理继续复用现有 processor / queue / task 查询逻辑

### 8.5 安全与边界

若后续做 `Streamable HTTP`：

- 优先只绑定本地
- 明确鉴权与 Origin 校验
- 避免将本地文件系统能力无边界暴露给远端客户端

## 9. 下一位 Agent 的推荐执行顺序

1. 以 `main` 为唯一基线，禁止直接合并 `dev`。
2. 修复字幕接口断点，恢复 Web 到 API 的闭环。
3. 复核历史记录模块是否应接入主流程。如果接入，先定义最小接入点，再补测试。
4. 梳理 MCP MVP 的 Tool 边界，确认是否完全复用现有 `task_id` 和队列模型。
5. 实现 `stdio` MCP Server。
6. 为 MCP 增加最小测试和使用说明。
7. 仅在 `stdio` 稳定后，再决定是否上 `Streamable HTTP`。

## 10. 建议的验证清单

在继续开发前，建议至少验证以下内容：

- `python api.py` 能正常启动
- `/api` 与 `/health` 正常返回
- B 站、本地音频、批量处理的任务提交链路正常
- 任务列表、任务取消、结果下载链路正常
- 字幕页面是否因接口不一致而失效
- 历史记录模块是否真的未接入主流程
- `pytest` 是否覆盖当前拟修改区域

在开始 MCP 开发后，建议新增最小验证：

- MCP Tool 能正常提交任务并返回 `task_id`
- MCP Tool 能查询任务状态
- 任务完成后能读取文本结果或输出元数据
- 异常时能返回稳定错误，不泄露不必要内部信息

## 11. 明确的非目标

在没有额外确认前，本阶段不应默认执行：

- 不做 `dev` 到 `main` 的直接合并
- 不做分布式任务系统重构
- 不做数据库持久化大改
- 不做前端技术栈整体替换
- 不做与 MCP 无关的大规模目录重构

## 12. 给下一位 Agent 的一句话总结

请把这个仓库当作“已经收敛到 `main` 的单机 `MVP`”，先修主线断点，再以最小侵入方式给它加一个复用现有队列和任务模型的 MCP `stdio` 入口；`dev` 只能当参考资料，不能当待合并主线。
