# 开发指南（MVP）

## 1. 开发环境

### 1.1 Python 依赖

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 1.2 前端依赖（仅前端开发需要）

```bash
npm install
npm run dev
```

### 1.3 环境变量

```bash
cp .env.example .env
```

至少配置一个可用 API Key（DeepSeek / Gemini / DashScope / Cerebras）。

## 2. 本地运行

```bash
# API + Web
python "api.py"

# CLI
python "main.py"
```

## 3. 代码质量与测试

```bash
# 单元测试
pytest

# 代码检查
ruff check .
ruff format .
```

Windows / Linux 也可使用脚本：

- `scripts/lint.bat`
- `scripts/lint.sh`

## 4. 目录结构（当前）

```text
src/
├── api/                  # 队列与 API 辅助逻辑
├── core/                 # 处理器、核心模型、异常、历史管理
├── services/             # ASR / 下载 / LLM / 字幕
├── text_arrangement/     # 润色、摘要、文本导出
└── utils/                # 配置、日志、设备、辅助工具
```

入口文件：

- `api.py`：FastAPI 服务入口
- `main.py`：CLI 入口

## 5. 配置要点

关键配置读取入口：`src/utils/config/manager.py`

- `ASR_MODEL`：`paraformer` / `sense_voice` / `whisper_cpp`
- `DEVICE`：`auto` / `cpu` / `cuda...`
- `USE_ONNX`：是否启用 ONNX 推理
- `LLM_SERVER`：主 LLM 服务
- `SUMMARY_LLM_SERVER`：摘要模型
- `OUTPUT_STYLE`：输出样式
- `DISABLE_LLM_POLISH` / `DISABLE_LLM_SUMMARY`

## 6. API 开发约束

- 处理类接口均走异步队列（提交即返回 `task_id`）
- 任务状态在内存中维护，重启后清空
- 结果下载统一通过 `GET /api/v1/download/{task_id}`

## 7. 文档维护原则（MVP）

- 仅保留当前可执行内容，不保留历史提案型文档。
- 接口变更时必须同步更新 `docs/user-guide/api-usage.md`。
- 启动命令变更时必须同步更新 `README.md` 和 `docs/deployment/docker.md`。
