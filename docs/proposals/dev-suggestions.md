# AutoVoiceCollation 开发者建议

> ✅ 项目版本：v2.0 | 状态：Phase 1 已完成，Phase 2 计划中

---

## 项目概述

AutoVoiceCollation 是一个基于 Python 的音视频转文本系统，集成 **ASR（FunASR）** 和 **LLM（多提供商）** 实现自动识别、润色与导出。

### 🛠️ 核心技术栈
- **ASR**：FunASR + PyTorch  
- **API 框架**：FastAPI  
- **前端 UI**：Web 前端 + Tailwind CSS  
- **LLM 集成**：DeepSeek, Gemini, Cerebras, Qwen 等多提供商  

### 🔁 处理流程
```
输入（B站/本地文件）
    ↓
下载/上传
    ↓
ASR 识别
    ↓
LLM 润色
    ↓
导出（PDF / 图片 / 字幕）
```

---

## 核心架构指南

### 1. 项目结构改进（优先级：中）✅ 已完成

#### ✅ 当前状态
已在 Phase 1 中完成重构。

#### ✅ 实现情况
```bash
src/
├── core/                  # ✅ 核心业务逻辑
│   ├── processors/        # ✅ 处理器模块（audio/video/subtitle）
│   ├── models/            # ✅ 数据模型（Pydantic/dataclass）
│   │   ├── task.py        # ✅ 任务模型
│   │   ├── video.py       # ✅ 视频模型
│   │   └── __init__.py
│   ├── exceptions/        # ✅ 异常定义
│   │   ├── base.py        # ✅ 基础异常
│   │   ├── asr.py         # ✅ ASR 异常
│   │   ├── llm.py         # ✅ LLM 异常
│   │   ├── task.py        # ✅ 任务异常
│   │   └── __init__.py
│   └── __init__.py
├── services/              # ✅ 外部服务集成
│   ├── asr/               # ✅ ASR 服务
│   │   ├── base.py        # ✅ 服务基类
│   │   ├── factory.py     # ✅ 工厂模式
│   │   ├── paraformer.py  # ✅ Paraformer 实现
│   │   ├── sense_voice.py # ✅ SenseVoice 实现
│   │   └── __init__.py
│   ├── llm/               # ✅ LLM 服务
│   │   ├── models.py      # ✅ 数据模型
│   │   ├── factory.py     # ✅ 统一查询接口
│   │   └── __init__.py
│   └── __init__.py
├── utils/                 # ✅ 工具类
│   ├── config/            # ✅ 配置管理（Pydantic v2）
│   │   ├── base.py        # ✅ 配置基类
│   │   ├── paths.py       # ✅ 路径配置
│   │   ├── llm.py         # ✅ LLM 配置
│   │   ├── asr.py         # ✅ ASR 配置
│   │   ├── logging.py     # ✅ 日志配置
│   │   ├── manager.py     # ✅ 配置管理器
│   │   └── __init__.py
│   ├── logging/           # ✅ 日志系统
│   │   └── logger.py
│   ├── device/            # ✅ 设备管理
│   │   └── device_manager.py
│   ├── helpers/           # ✅ 辅助工具
│   │   ├── task_manager.py
│   │   ├── timer.py
│   │   └── __init__.py
│   └── __init__.py
├── api/                   # ✅ API 层
│   ├── middleware/        # ✅ 中间件
│   │   ├── error_handler.py   # ✅ 错误处理
│   │   └── __init__.py
│   └── __init__.py
└── __init__.py
```

#### ✅ 已实现收益
- ✅ 清晰的职责分离（单一职责原则）
- ✅ 提高代码可维护性
- ✅ 降低模块耦合度
- ✅ 便于团队协作

#### ⏱️ 实际工时
约 **10 小时**（Phase 1）

---

### 2. 配置管理现代化（优先级：高）✅ 已完成

#### ✅ 当前状态
已在 Phase 1 中完成。

#### ✅ 实现方案
使用 **Pydantic v2** 构建类型安全的配置系统。

```python
# src/utils/config/base.py
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class BaseConfig(BaseSettings):
    """配置基类"""
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_assignment=True,
    )
```

```python
# src/utils/config/paths.py
from pathlib import Path
from pydantic import Field

class PathConfig(BaseConfig):
    """路径配置"""
    output_dir: Path = Field(default_factory=lambda: Path("out"))
    download_dir: Path = Field(default_factory=lambda: Path("download"))
    temp_dir: Path = Field(default_factory=lambda: Path("temp"))
    log_dir: Path = Field(default_factory=lambda: Path("logs"))
    model_dir: Optional[Path] = Field(default=None)
```

```python
# src/utils/config/llm.py
class LLMConfig(BaseConfig):
    """LLM 配置"""
    llm_server: str = Field(default="Cerebras:Qwen-3-235B-Instruct")
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=6000, ge=1, le=32000)

    # API Keys
    deepseek_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    dashscope_api_key: Optional[str] = None
    cerebras_api_key: Optional[str] = None
```

#### ✅ 使用示例
```python
from src.utils.config import get_config
config = get_config()
print(config.paths.output_dir)
print(config.llm.llm_server)
```

#### ✅ 已实现收益
- ✅ 类型安全配置
- ✅ 自动验证与转换
- ✅ 环境变量清晰分离
- ✅ IDE 自动补全支持
- ✅ 向后兼容层（便于迁移）

#### ⏱️ 实际工时
约 **8 小时**

#### 📚 相关文档
- `src/config.py` — 废弃警告与迁移指南
- `docs/proposals/legacy-module-migration.md` — Phase 2 迁移计划

---

### 3. 统一异常处理（优先级：高）✅ 已部分完成

#### ✅ 当前状态
核心异常已定义，部分已集成。

#### ✅ 实现方案
```python
# src/core/exceptions/base.py
from typing import Optional

class AutoVoiceCollationError(Exception):
    """项目基础异常"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)
```

```python
# src/core/exceptions/asr.py
class ASRError(AutoVoiceCollationError):
    """ASR 相关异常"""
    def __init__(self, message: str, model: str = None):
        code = f"ASR_ERROR_{model.upper()}" if model else "ASR_ERROR"
        super().__init__(message, code)
```

```python
# src/api/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
from src.core.exceptions import AutoVoiceCollationError
from datetime import datetime

async def auto_voice_collation_error_handler(
    request: Request, exc: AutoVoiceCollationError
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": exc.message,
            "code": exc.code,
            "type": exc.__class__.__name__,
            "timestamp": datetime.now().isoformat()
        }
    )

# 注册中间件
register_exception_handlers(app)
```

#### ✅ 已实现收益
- ✅ 统一错误响应格式
- ✅ 清晰的错误码系统
- ✅ 易于调试和维护
- ✅ 更好的 API 体验

#### ⏱️ 实际工时
约 **5 小时**

#### ⏳ 待完成
- 在更多地方使用自定义异常替代通用异常
- 添加更详细的错误分类

---

### 4. 类型安全增强（优先级：中）🔄 进行中

#### ❗ 当前问题
- 大量使用字典传递数据
- 部分代码缺少类型提示
- 运行时错误风险较高

#### ✅ 已完成部分
- ✅ 创建 `LLMQueryParams` dataclass
- ✅ 创建 `BiliVideoFile` dataclass
- ✅ 配置系统全面使用 Pydantic

#### 💡 建议继续
##### 方式 1：`TypedDict`（兼容现有代码）
```python
from typing import TypedDict, Optional
from datetime import datetime

class TaskResult(TypedDict):
    task_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    result: Optional[dict]
    error: Optional[str]
```

##### 方式 2：`Pydantic Models`（推荐）
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TaskResult(BaseModel):
    task_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None

# 自动验证
result = TaskResult(task_id="123", status="completed", created_at=datetime.now())
```

#### ⏳ 待实现
1. 为任务数据创建 `Task` model  
2. 为 API 响应创建完整 Pydantic schemas  
3. 配置 `mypy` 进行静态类型检查

#### ✅ 预期收益
- 编译期类型检查（配合 mypy）
- 减少运行时错误
- IDE 自动补全
- 自动生成 OpenAPI 文档

#### ⏱️ 预估工时
6–10 小时

---

### 5. 测试策略改进（优先级：高）✅ 已有基础

#### ✅ 当前状态
- ✅ 基础单元测试覆盖
- ✅ pytest 配置已设置
- ✅ 测试标记（unit, integration, slow）已配置

#### 📁 测试结构
```python
# tests/integration/test_api_workflow.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_bilibili_workflow():
    """测试完整的 B站视频处理流程"""
    # 实现集成测试
```

```python
# tests/performance/test_asr_performance.py
@pytest.mark.performance
@pytest.mark.slow
def test_asr_latency():
    """测试 ASR 推理延迟"""
    import time
    start = time.time()
    # 执行 ASR
    elapsed = time.time() - start
    assert elapsed < 10.0  # 10秒内完成
```

#### 📝 `pytest.ini` 配置
```ini
[pytest]
markers =
    unit: 单元测试（默认）
    integration: 集成测试（需要外部服务）
    slow: 慢速测试
    performance: 性能测试
    asyncio: 异步测试
```

#### 🚀 运行命令
```bash
pytest -m "not slow and not integration"  # 快速测试
pytest -m integration                      # 运行集成测试
pytest -n auto                             # 并行测试（需 pytest-xdist）
pytest --cov=src tests/                    # 测试覆盖率
```

#### ⏳ 待改进
- 增加集成测试覆盖率
- 添加性能基准测试
- 配置 CI/CD 自动运行测试

#### ⏱️ 预估工时
12–20 小时（持续改进）

---

### 6. 监控和可观测性（优先级：中）⏳ 待实现

#### ❗ 当前问题
- 缺少性能指标
- 日志已结构化但可进一步优化
- 无法追踪请求链路

#### ✅ 建议方案：Prometheus + Grafana
```python
# src/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge

TASKS_PROCESSED = Counter(
    'autovoice_tasks_processed_total',
    'Total number of tasks processed',
    ['type', 'status']
)

ASR_PROCESSING_TIME = Histogram(
    'autovoice_asr_processing_seconds',
    'ASR processing time in seconds',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

ACTIVE_TASKS = Gauge(
    'autovoice_active_tasks',
    'Number of currently active tasks'
)

# 使用示例
TASKS_PROCESSED.labels(type='bilibili', status='success').inc()
ASR_PROCESSING_TIME.observe(processing_time)
ACTIVE_TASKS.set(len(active_tasks))
```

#### 📝 日志结构化（可选）
```python
# src/utils/logging.py
import structlog

logger = structlog.get_logger()

logger.info("task_started", task_id=task_id, type=task_type)
logger.error("asr_failed", error=str(e), audio_file=audio_path)
```

#### ✅ 健康检查端点（已实现）
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "asr_model": config.asr.asr_model,
            "llm_server": config.llm.llm_server,
            "output_dir": str(config.paths.output_dir)
        }
    }
```

#### ✅ 预期收益
- 实时监控关键指标
- 快速定位问题
- 性能优化依据
- 自动化告警

#### ⏱️ 预估工时
20–32 小时

---

### 7. 前端现代化（优先级：低）⏳ 待评估

#### ✅ 当前状态
- ✅ Web 前端 提供基础 UI
- ✅ Tailwind CSS 已集成
- ⏳ 可考虑迁移到现代框架

#### 💡 建议方案：Vue.js 3 + Vite
```html
<!-- frontend/src/App.vue -->
<template>
  <div id="app">
    <TaskManager />
    <HistoryPanel />
    <SettingsPanel />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import TaskManager from './components/TaskManager.vue'
import HistoryPanel from './components/HistoryPanel.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const activeTasks = ref([])
</script>
```

#### 📦 状态管理：Pinia
```javascript
// frontend/src/stores/taskStore.js
import { defineStore } from 'pinia'

export const useTaskStore = defineStore('task', {
  state: () => ({
    tasks: [],
    activeTaskId: null,
    history: []
  }),
  actions: {
    async submitTask(taskData) {
      // 提交任务
    },
    async cancelTask(taskId) {
      // 取消任务
    }
  }
})
```

#### ✅ 预期收益
- 更好的用户体验
- 更丰富的交互功能
- 支持状态管理
- 可扩展架构

#### ⏱️ 预估工时
40–60 小时

#### 📌 建议
当前 Web 前端 + Tailwind 方案已满足基本需求，**可暂缓**。

---

### 8. 生产部署优化（优先级：中）✅ Docker 已实现

#### ✅ 当前状态
- ✅ Docker 支持（CPU/GPU 版本）
- ✅ docker-compose 配置
- ✅ 健康检查已实现

#### ✅ 优化建议：多阶段构建
```dockerfile
# Dockerfile.optimized
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH

RUN useradd -m -u 1000 appuser
USER appuser

CMD ["python", "api.py"]
```

#### 📦 Kubernetes 配置（如需）
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autovoicecollation
spec:
  replicas: 2
  selector:
    matchLabels:
      app: autovoicecollation
  template:
    metadata:
      labels:
        app: autovoicecollation
    spec:
      containers:
      - name: api
        image: autovoicecollation:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

#### ✅ 预期收益
- 镜像体积减少 50–70%
- 支持自动扩缩容
- 提升部署稳定性
- 资源使用可控

#### ⏱️ 预估工时
12–20 小时

---

## Phase 2 迁移计划

详见：[`docs/proposals/legacy-module-migration.md`](./legacy-module-migration.md)

### ⏳ 待迁移模块
- `bilibili_downloader.py` → `src/services/download/`
- `device_manager.py`（清理旧版本）
- `extract_audio_text.py` → `src/services/asr/` 或 `src/core/`
- `logger.py`（清理旧版本）
- `output_file_manager.py` → `src/core/export/`
- `process_history.py` → `src/core/history/`
- `subtitle_generator.py` → `src/services/subtitle/`
- `task_manager.py`（清理旧版本）
- `Timer.py`（清理旧版本）
- ✅ 保留 `core_process.py` 作为向后兼容层

#### ⏱️ 预估总工时
2–3 周

---

## 整体规划建议

### ✅ 第一阶段（基础建设）：已完成
1. **配置管理现代化**（8h）  
   - 使用 Pydantic v2 重构配置系统
   - 增加类型验证
   - 支持多环境配置
2. **统一异常处理**（5h）  
   - 定义项目级异常类
   - 创建错误处理中间件
   - 统一响应格式
3. **项目结构重构**（10h）  
   - 模块化划分
   - 整理导入关系
   - 更新测试文件

### 🔄 第二阶段（质量提升）：进行中
1. **类型安全增强**（6–10h）  
   - 添加类型注解
   - 配置 mypy
   - 修复类型错误
2. **测试策略改进**（12–20h）  
   - 补充单元/集成测试
   - 建立 CI/CD 流水线
   - 提高覆盖率

### ⏳ 第三阶段（架构优化）：计划中
1. **遗留模块迁移**（2–3 周）  
   - 逐步迁移，保持兼容
   - 完善文档
2. **监控和可观测性**（20–32h）  
   - Prometheus + Grafana
   - 结构化日志
   - 健康检查增强

### ⏳ 第四阶段（功能增强）：待评估
1. **前端现代化**（40–60h）— 可选  
   - 评估是否需迁移到 Vue.js 3
   - 当前 Web 前端 方案已满足需求
2. **生产部署优化**（12–20h）  
   - 优化 Docker 镜像
   - 考虑 Kubernetes 部署

---

## 技术选型建议

### 必选项
- ✅ Pydantic v2 — 配置与数据验证
- ✅ FastAPI — API 框架
- ✅ pytest — 测试框架
- ⏳ mypy — 静态类型检查（建议添加）

### 推荐项
- ⏳ Prometheus + Grafana — 监控与可视化
- ⏳ structlog — 结构化日志（可选）
- ✅ pytest-xdist — 并行测试
- ✅ Coverage.py — 测试覆盖率

### 可选项
- ⏳ Vue.js 3 — 前端框架（按需评估）
- ⏳ Kubernetes — 容器编排（大规模部署）
- ⏳ Redis — 缓存与任务队列
- ⏳ PostgreSQL — 持久化存储

---

## 开发规范

### 代码质量要求
1. ✅ 所有公共函数必须有类型注解  
2. ✅ 所有类和函数必须有 docstring  
3. ✅ 新增代码应有对应测试  
4. ✅ 必须捕获并处理所有异常  
5. ✅ 关键操作必须记录日志

### 提交规范
使用 [Conventional Commits](https://www.conventionalcommits.org/)：
```bash
git commit -m "feat(auth): add user authentication"
git commit -m "fix(api): resolve response timeout issue"
git commit -m "docs(readme): update installation guide"
git commit -m "refactor(config): migrate to pydantic v2"
git commit -m "test(api): add endpoint tests"
```

---

## 参考资料

- [CLAUDE.md](../CLAUDE.md) — 完整项目文档
- [legacy-module-migration.md](./legacy-module-migration.md) — Phase 2 迁移计划
- [ROADMAP.md](./ROADMAP.md) — 项目路线图
- API 文档：[http://localhost:8000/docs](http://localhost:8000/docs)

---

- **最后更新**：2025-12-17  
- **文档版本**：2.0  
- **状态**：Phase 1 已完成，Phase 2 计划中  

✅ 本文档已优化，适合用于团队协作、CI/CD 配置、代码审查与新成员入职培训。  
如需导出 PDF / HTML，也可继续协助。
