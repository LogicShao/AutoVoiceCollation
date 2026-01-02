## 1) MCP 是什么（Model Context Protocol）

**MCP（Model Context Protocol）**是一套开放协议，用来把“LLM 应用（Host）”和“外部工具/数据（Server）”用统一方式连起来，让模型能**安全、标准化地获取上下文、调用工具、执行工作流**。([Model Context Protocol][1])

它的通信基于 **JSON-RPC 2.0**，并且把参与方分成三类：

* **Host**：承载 LLM 的应用（例如桌面助手/IDE/Chat 应用）
* **Client**：Host 内部的连接器（负责和 MCP Server 对话）
* **Server**：对外提供能力（数据、工具、提示模板）的服务([Model Context Protocol][1])

### MCP Server 能提供哪些能力？

MCP 规范里，Server 主要提供三类“对 LLM 有用的东西”：

* **Resources**：可被读取的上下文/数据（类似“可加载进上下文的 GET”）
* **Tools**：可被调用执行的函数（类似“带副作用或产出结果的 POST”）
* **Prompts**：可复用的提示模板/工作流([Model Context Protocol][1])

### MCP 怎么跑起来（传输方式）？

最新规范定义了两种标准传输：

1. **stdio**：本地子进程方式（客户端启动 server，用 stdin/stdout 传 JSON-RPC）
2. **Streamable HTTP**：HTTP 单端点（POST/GET，可选 SSE 流式），替代旧版的 HTTP+SSE([Model Context Protocol][2])

---

## 2) 看完你的项目文档：它很适合做成 MCP Server 吗？

### 你这个项目现在是什么形态？

从 README 来看，AutoVoiceCollation 已经是一个“非常标准的可工具化能力集合”：

* 多源输入：B 站视频、本地音视频文件
* ASR：SenseVoice / Paraformer
* LLM 润色/摘要：DeepSeek、Qwen、Gemini、Cerebras、本地模型等
* 多格式输出：PDF/图片/文本/SRT
* 提供三种使用方式：CLI / Web 前端 / RESTful API([GitHub][3])

并且你已经提供了 **API 服务**，核心端点也很清晰：

* `POST /api/v1/process/bilibili`
* `POST /api/v1/process/audio`
* `GET /api/v1/task/{task_id}`([GitHub][3])

---

## 结论：**非常适合**作为 MCP Server 的候选（而且你现在正好处在“最适合转 MCP”的阶段）

原因很直接：

1. **你的能力天然就是“Tools”**
   处理 B 站 / 处理音频 / 查任务状态，这些就是典型的 MCP tools 映射。([GitHub][3]) ([Model Context Protocol][1])

2. **你的输出天然就是“Resources”**
   转录文本、润色稿、摘要、PDF/SRT 等，都可以用 MCP resources 暴露出来，让 LLM“读取并引用”。([Model Context Protocol][1]) ([GitHub][3])

3. **你已经有 FastAPI + 异步任务模型**
   MCP 规范里提到进度跟踪、取消、错误报告等机制，你的 `task_id` 模式非常容易对齐成 MCP 的“长任务 + 进度”。([Model Context Protocol][1]) ([GitHub][3])

4. **生态与实现成本低**（Python）
   官方的 MCP Python SDK（PyPI 包名就是 `mcp`）已经提供 `FastMCP`，并且支持 stdio 与 Streamable HTTP。([PyPI][4])

---

## 建议你“下一步”怎么做：两条路线，推荐从 A 开始

### 路线 A（最顺滑）：把现有 FastAPI API 适配成 MCP（Streamable HTTP）

你已经有 `python api.py` 和 `/docs`（FastAPI swagger），那就新增一个 MCP endpoint（例如 `/mcp`），用 MCP Python SDK 挂载进去即可。SDK 本身就支持“挂载到现有 ASGI Server / Streamable HTTP”。([PyPI][4])

**你可以先做 3 个 MCP tools（MVP）：**

* `process_bilibili(url, options...) -> task_id`
* `process_audio(path_or_url, options...) -> task_id`
* `get_task(task_id) -> status + progress + result_uris`

再做 2～3 个 resources（让模型能读结果）：

* `avc://task/{task_id}/transcript`
* `avc://task/{task_id}/summary`
* `avc://task/{task_id}/output/pdf`（返回可下载路径或本地文件引用）

> 注意：如果你把 MCP 用 Streamable HTTP 暴露到局域网/公网，要按规范做安全措施（校验 Origin、优先绑定 localhost、鉴权等），否则会有 DNS rebinding 风险。([Model Context Protocol][2])

### 路线 B（最简单本地集成）：做一个 stdio MCP Server（本地子进程）

如果你主要目标是“让 Claude Desktop / IDE 在本地调用你的能力”，stdio 是最快的：客户端拉起你的 server 子进程，你只处理 stdin/stdout 的 JSON-RPC。([Model Context Protocol][2])

---

## 一个很实用的对照表：把你现有 API 映射到 MCP

| 现有能力           | 现在形式                                         | MCP 里更像什么                                                                    |         |           |
| -------------- | -------------------------------------------- | ---------------------------------------------------------------------------- | ------- | --------- |
| 处理 B 站视频       | `POST /api/v1/process/bilibili`([GitHub][3]) | Tool：`process_bilibili`                                                      |         |           |
| 处理音频文件         | `POST /api/v1/process/audio`([GitHub][3])    | Tool：`process_audio`                                                         |         |           |
| 查询任务状态         | `GET /api/v1/task/{task_id}`([GitHub][3])    | Tool：`get_task` 或 Resource：`avc://task/{id}/status`                          |         |           |
| 转录/润色/摘要结果     | 输出文件/文本([GitHub][3])                         | Resources：`avc://task/{id}/transcript                                        | summary | polished` |
| “帮我把这段会议整理成纪要” | 需要用户手写 prompt                                | Prompt：`meeting_minutes(style=..., length=...)`([Model Context Protocol][1]) |         |           |

---

## 你做成 MCP 时，最容易踩的 3 个坑（提前规避）

1. **大文件输入**（音频/视频）
   MCP 消息本身不适合直接塞巨大二进制。建议 MCP tool 参数只接：

   * 本地路径（stdio 场景最自然）
   * 可访问 URL（bilibili/网盘直链）
   * 或“先上传到你的 API，再返回 task_id”（你已经有 API 体系）

2. **长任务与进度**
   你已经有 task_id，非常好：在 MCP tool 返回 task_id，并通过后续查询 tool/resource 获取进度与结果即可。

3. **安全边界**
   MCP 的能力很强（工具执行、数据访问），规范明确强调用户同意、数据隐私与安全控制。([Model Context Protocol][1])
   尤其是 Streamable HTTP 场景要做好 Origin 校验、鉴权、最小权限。([Model Context Protocol][2])

---

## 你可以直接参考的官方实现路径（Python）

MCP Python SDK 的 Quickstart 就是用 `FastMCP` 定义 tool/resource/prompt，然后 `run(transport="streamable-http")`。([PyPI][4])
所以你这边基本就是：把现有 `core_process` / FastAPI handler 复用出来，挂到 `@mcp.tool()` 上。


[1]: https://modelcontextprotocol.io/specification/2025-06-18 "Specification - Model Context Protocol"
[2]: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports "Transports - Model Context Protocol"
[3]: https://github.com/LogicShao/AutoVoiceCollation "GitHub - LogicShao/AutoVoiceCollation: AutoVoiceCollation 是一个功能强大的自动语音识别（ASR）和文本处理工具，旨在帮助用户快速整理和润色语音转录文本。"
[4]: https://pypi.org/project/mcp/ "mcp · PyPI"
