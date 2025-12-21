# 异步推理队列架构设计方案

- **方案编号**：ARCH-001  
- **优先级**：P0（高优先级）  
- **预计实施时间**：2–4 小时  
- **目标**：解决 FastAPI 推理阻塞问题，实现真正的异步 HTTP 响应  

---

## 一、问题背景

### 1.1 当前架构存在的问题

#### ❌ 核心问题
FastAPI 虽使用 `async def` 和 `BackgroundTasks`，但后台任务内部调用的是 **同步阻塞函数**，导致整个服务在模型推理期间无法响应其他 HTTP 请求。

#### ❌ 问题表现
```python
# api.py:327 - 虽为 async，但内部是同步阻塞
async def process_bilibili_task(task_id: str, ...):
    # ❌ 同步函数，会占用事件循环
    output_data, extract_time, polish_time, zip_file = bilibili_video_download_process(...)
```

#### ❌ 影响范围
- ✘ 推理期间（10秒–5分钟），无法响应健康检查 `/health`
- ✘ 无法查询任务状态 `/api/v1/task/{task_id}`
- ✘ 无法提交新任务
- ✘ Web UI 前端无法获取进度更新

---

### 1.2 为什么 `ProcessPoolExecutor` 不适合？

| 问题维度       | `ProcessPoolExecutor` 方案           | 本地部署现实                     |
|----------------|----------------------------------|------------------------------|
| **模型加载**     | 每个进程独立加载模型                  | Paraformer: ~1.5GB × 4 = 6GB       |
| **GPU 显存**     | 多进程竞争单个 GPU                   | CUDA OOM 或推理慢 3–5x             |
| **初始化时间**   | 每次请求冷启动                       | 模型加载 15–30 秒/进程              |
| **本地资源**     | 需多核 CPU + 大内存                 | 个人电脑资源有限                   |

#### 📌 根本原因
- PyTorch 模型非线程/进程安全
- CUDA context 无法跨进程共享
- 本地单 GPU 环境无需并发推理

---

## 二、解决方案：单进程异步推理队列

### 2.1 核心设计思想

#### ✅ 设计原则
1. **单进程单模型**：全局唯一模型实例，避免重复加载
2. **异步任务队列**：使用 `asyncio.Queue` 管理推理任务
3. **线程池执行器**：通过 `run_in_executor` 避免阻塞事件循环
4. **HTTP 异步响应**：FastAPI 立即返回 `task_id`，客户端轮询状态

### 2.2 架构设计

```mermaid
graph TD
    A[用户 HTTP 请求] --> B[FastAPI 异步端点]
    B --> C{立即返回 202 Accepted + task_id}
    C --> D[asyncio.Queue.put()]
    D --> E[InferenceQueue（单例）]
    E --> F[Worker Loop]
    F --> G[await queue.get()]
    G --> H[run_in_executor(None, sync_func)]
    H --> I[ThreadPoolExecutor]
    I --> J[同步推理函数]
    J --> K[更新任务状态到内存]
    K --> L[客户端轮询 GET /task/{task_id}]
```

> ✅ 关键点：`run_in_executor` 将 CPU 密集型任务移出事件循环，保证 HTTP 可持续响应。

---

### 2.3 关键技术点

#### 2.3.1 为什么 HTTP 请求不会阻塞？
```python
@app.post("/api/v1/process/bilibili")
async def process_bilibili_video(request: BilibiliVideoRequest):
    task_id = str(uuid.uuid4())
    
    # ✅ 立即返回，不等待推理完成
    await inference_queue.submit_task(task_id, request)
    
    return {"task_id": task_id, "status": "pending"}
    # ← 客户端立即收到响应
```

#### 2.3.2 为什么模型推理不阻塞事件循环？
```python
async def _worker_loop(self):
    while True:
        task_item = await self.queue.get()  # ✅ 异步等待
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,  # 使用默认线程池
            self._sync_inference,
            task_item
        )
        # ← 推理在单独线程中执行
```

#### 2.3.3 模型单次加载机制
```python
class InferenceQueue:
    def __init__(self):
        self._model = None
        self._model_lock = asyncio.Lock()

    async def _ensure_model_loaded(self):
        if self._model is None:
            async with self._model_lock:
                if self._model is None:
                    self._model = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._load_model_sync
                    )
```

---

## 三、代码实现

### 3.1 推理队列核心类

#### 📂 文件路径：`src/api/inference_queue.py`

```python
"""
异步推理队列
提供单进程、单模型实例的异步推理能力
"""

import asyncio
from asyncio import Queue
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import traceback

from src.logger import get_logger
from src.core_process import bilibili_video_download_process, upload_audio
from src.text_arrangement.summary_by_llm import summarize_text

logger = get_logger(__name__)


class InferenceQueue:
    """
    异步推理队列（单例模式）

    设计原则：
    - 全局唯一实例，持有唯一模型
    - 串行处理任务（避免 GPU 冲突）
    - 异步接口，不阻塞 FastAPI 事件循环
    """

    _instance: Optional['InferenceQueue'] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化队列（仅执行一次）"""
        if self._initialized:
            return

        self.queue: Queue = Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self._model = None  # 延迟加载
        self._model_lock = asyncio.Lock()
        self._initialized = True

        logger.info("推理队列初始化完成")

    async def start(self):
        """启动工作循环"""
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker_loop())
            logger.info("✅ 推理工作线程已启动")

    async def stop(self):
        """停止工作循环"""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                logger.info("推理工作线程已停止")

    async def submit_task(
        self,
        task_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        tasks_store: Dict
    ):
        """
        提交任务到队列

        :param task_id: 任务 ID
        :param task_type: 任务类型（bilibili, audio, batch, subtitle）
        :param task_data: 任务数据
        :param tasks_store: 任务状态存储（引用传递）
        """
        await self.queue.put({
            'task_id': task_id,
            'task_type': task_type,
            'task_data': task_data,
            'tasks_store': tasks_store
        })
        logger.info(f"任务已提交到队列: {task_id}, 队列长度: {self.queue.qsize()}")

    async def _worker_loop(self):
        """工作循环：持续从队列取任务并执行"""
        logger.info("工作循环已启动，等待任务...")

        while True:
            try:
                task_item = await self.queue.get()

                task_id = task_item['task_id']
                task_type = task_item['task_type']
                task_data = task_item['task_data']
                tasks_store = task_item['tasks_store']

                logger.info(f"开始处理任务: {task_id}, 类型: {task_type}")

                try:
                    # 更新状态为处理中
                    tasks_store[task_id]['status'] = 'processing'

                    # 根据类型调用处理函数
                    if task_type == 'bilibili':
                        await self._process_bilibili_task(task_id, task_data, tasks_store)
                    elif task_type == 'audio':
                        await self._process_audio_task(task_id, task_data, tasks_store)
                    elif task_type == 'batch':
                        await self._process_batch_task(task_id, task_data, tasks_store)
                    elif task_type == 'subtitle':
                        await self._process_subtitle_task(task_id, task_data, tasks_store)
                    else:
                        raise ValueError(f"未知的任务类型: {task_type}")

                    logger.info(f"✅ 任务完成: {task_id}")

                except Exception as e:
                    logger.error(f"❌ 任务失败: {task_id}, 错误: {e}", exc_info=True)
                    tasks_store[task_id].update({
                        'status': 'failed',
                        'message': f"处理失败: {str(e)}",
                        'error': traceback.format_exc(),
                        'completed_at': datetime.now().isoformat()
                    })

                finally:
                    self.queue.task_done()

            except asyncio.CancelledError:
                logger.info("工作循环被取消")
                break
            except Exception as e:
                logger.error(f"工作循环异常: {e}", exc_info=True)

    async def _process_bilibili_task(self, task_id: str, data: Dict, tasks_store: Dict):
        """处理 B站视频任务"""
        loop = asyncio.get_event_loop()

        output_data, extract_time, polish_time, zip_file = await loop.run_in_executor(
            None,
            bilibili_video_download_process,
            data['video_url'],
            data['llm_api'],
            data['temperature'],
            data['max_tokens'],
            data['text_only']
        )

        completed_at = datetime.now().isoformat()

        if data['text_only']:
            result_data = output_data

            if data.get('summarize') and 'polished_text' in result_data:
                tasks_store[task_id]['message'] = '正在生成总结'
                summary = await loop.run_in_executor(
                    None,
                    summarize_text,
                    result_data['polished_text'],
                    data['llm_api'],
                    data['temperature'],
                    data['max_tokens'],
                    result_data.get('title', '')
                )
                result_data['summary'] = summary
                completed_at = datetime.now().isoformat()

            tasks_store[task_id].update({
                'status': 'completed',
                'message': '处理完成',
                'result': result_data,
                'completed_at': completed_at
            })
        else:
            tasks_store[task_id].update({
                'status': 'completed',
                'message': '处理完成',
                'result': {
                    'output_dir': output_data,
                    'extract_time': extract_time,
                    'polish_time': polish_time,
                    'zip_file': zip_file
                },
                'completed_at': completed_at
            })

    async def _process_audio_task(self, task_id: str, data: Dict, tasks_store: Dict):
        """处理音频任务"""
        import os
        loop = asyncio.get_event_loop()

        output_data, extract_time, polish_time, zip_file = await loop.run_in_executor(
            None,
            upload_audio,
            data['audio_path'],
            data['llm_api'],
            data['temperature'],
            data['max_tokens'],
            data['text_only']
        )

        # 清理临时文件
        if os.path.exists(data['audio_path']):
            await loop.run_in_executor(
                None,
                os.remove,
                data['audio_path']
            )

        completed_at = datetime.now().isoformat()

        if data['text_only']:
            result_data = output_data

            if data.get('summarize') and 'polished_text' in result_data:
                tasks_store[task_id]['message'] = '正在生成总结'
                summary = await loop.run_in_executor(
                    None,
                    summarize_text,
                    result_data['polished_text'],
                    data['llm_api'],
                    data['temperature'],
                    data['max_tokens'],
                    result_data.get('title', '')
                )
                result_data['summary'] = summary
                completed_at = datetime.now().isoformat()

            tasks_store[task_id].update({
                'status': 'completed',
                'message': '处理完成',
                'result': result_data,
                'completed_at': completed_at
            })
        else:
            tasks_store[task_id].update({
                'status': 'completed',
                'message': '处理完成',
                'result': {
                    'output_dir': output_data,
                    'extract_time': extract_time,
                    'polish_time': polish_time,
                    'zip_file': zip_file
                },
                'completed_at': completed_at
            })

    async def _process_batch_task(self, task_id: str, data: Dict, tasks_store: Dict):
        """处理批量任务"""
        from src.core_process import process_multiple_urls
        loop = asyncio.get_event_loop()

        results = await loop.run_in_executor(
            None,
            process_multiple_urls,
            data['urls'],
            data['llm_api'],
            data['temperature'],
            data['max_tokens'],
            data['text_only']
        )

        tasks_store[task_id].update({
            'status': 'completed',
            'message': '批量处理完成',
            'result': results,
            'completed_at': datetime.now().isoformat()
        })

    async def _process_subtitle_task(self, task_id: str, data: Dict, tasks_store: Dict):
        """处理字幕任务"""
        from src.core_process import process_subtitles
        loop = asyncio.get_event_loop()

        output_path = await loop.run_in_executor(
            None,
            process_subtitles,
            data['video_path']
        )

        tasks_store[task_id].update({
            'status': 'completed',
            'message': '字幕生成完成',
            'result': {'output_video': output_path},
            'completed_at': datetime.now().isoformat()
        })


# 全局单例
_inference_queue: Optional[InferenceQueue] = None


def get_inference_queue() -> InferenceQueue:
    """获取全局推理队列实例"""
    global _inference_queue
    if _inference_queue is None:
        _inference_queue = InferenceQueue()
    return _inference_queue
```

---

### 3.2 修改 FastAPI 主文件

#### 📂 文件路径：`api.py`

##### 步骤 1：导入推理队列
```python
# api.py 顶部添加
from src.api.inference_queue import get_inference_queue

# 获取全局推理队列实例
inference_queue = get_inference_queue()
```

##### 步骤 2：添加生命周期事件
```python
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("启动 FastAPI 服务...")
    await inference_queue.start()
    logger.info("✅ 推理队列已启动")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("关闭 FastAPI 服务...")
    await inference_queue.stop()
    logger.info("✅ 推理队列已停止")
```

##### 步骤 3：修改 API 端点
```python
@app.post("/api/v1/process/bilibili", response_model=TaskResponse)
async def process_bilibili_video(request: BilibiliVideoRequest):
    """处理 B站视频（异步队列版本）"""
    task_id = str(uuid.uuid4())

    # 创建任务记录
    tasks[task_id] = {
        "status": "pending",
        "message": "任务已提交，等待处理",
        "result": None,
        "created_at": datetime.now().isoformat(),
        "url": request.video_url,
        "filename": None
    }

    # ✅ 提交任务到异步队列（立即返回）
    await inference_queue.submit_task(
        task_id=task_id,
        task_type='bilibili',
        task_data={
            'video_url': request.video_url,
            'llm_api': request.llm_api,
            'temperature': request.temperature,
            'max_tokens': request.max_tokens,
            'text_only': request.text_only,
            'summarize': request.summarize
        },
        tasks_store=tasks  # 引用传递，队列可直接更新状态
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="任务已提交到队列",
        created_at=tasks[task_id]["created_at"]
    )
```

##### 步骤 4：删除旧的后台任务函数
```python
# ❌ 删除以下函数
async def process_bilibili_task(...)
async def process_audio_task(...)
async def process_batch_task(...)
async def process_subtitle_task(...)
```

---

## 四、实施步骤

### 4.1 Phase 1：核心功能实现（2小时）

- [ ] 创建 `src/api/inference_queue.py`
- [ ] 实现 `InferenceQueue` 类
- [ ] 修改 `api.py` 导入推理队列
- [ ] 添加 `startup` 和 `shutdown` 事件处理
- [ ] 修改 `/api/v1/process/bilibili` 端点
- [ ] 修改 `/api/v1/process/audio` 端点
- [ ] 删除旧的后台任务函数

### 4.2 Phase 2：测试验证（1小时）

```bash
# 测试 1: 健康检查在推理时仍可响应
curl http://localhost:8000/health &
curl -X POST http://localhost:8000/api/v1/process/bilibili \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.bilibili.com/video/BV1xx411c7mD"}'

# 预期：health 立即返回 200

# 测试 2: 提交多个任务
for i in {1..3}; do
  curl -X POST http://localhost:8000/api/v1/process/bilibili \
    -H "Content-Type: application/json" \
    -d "{\"video_url\": \"https://www.bilibili.com/video/BV$i\"}" &
done

# 预期：所有请求立即返回 task_id，串行处理

# 测试 3: 查询任务状态
task_id="<从上面获取>"
curl http://localhost:8000/api/v1/task/$task_id
```

### 4.3 Phase 3：性能优化（1小时）

1. **添加队列容量限制**
```python
self.queue: Queue = Queue(maxsize=10)  # 最多10个待处理任务
```

2. **添加任务超时机制**
```python
async def _process_with_timeout(self, task_item, timeout=3600):
    try:
        await asyncio.wait_for(self._process_task(task_item), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"任务超时: {task_item['task_id']}")
        raise
```

3. **添加任务优先级**
```python
from asyncio import PriorityQueue
self.queue: PriorityQueue = PriorityQueue()
await self.queue.put((priority, task_item))
```

---

## 五、性能分析

### 5.1 资源占用对比

| 指标            | 原方案（BackgroundTasks） | 新方案（异步队列） |
|----------------|----------------------|-------------|
| **内存占用**      | 模型加载 1 次          | 模型加载 1 次    |
| **GPU 显存**    | 单进程独占              | 单进程独占       |
| **HTTP 响应时间** | 0.1–5分钟（阻塞）         | <50ms（立即返回） |
| **并发推理能力**    | 1 个任务               | 1 个任务（串行）   |
| **队列容量**      | 无限制                | 可配置（建议 10–50）|

### 5.2 适用场景

| ✅ 适合 | ❌ 不适合 |
|--------|----------|
| 本地单用户或小团队使用 | 高并发场景（每分钟数十任务） |
| 单 GPU/CPU 环境 | 多 GPU 服务器（无法利用并行） |
| 任务间隔 > 推理时间 | 生产级分布式部署 |

---

## 六、后续优化方向

### 方案 A：ONNX Runtime + 多线程
- 优势：2–4x 速度提升，支持多线程并发
- 劣势：需导出 ONNX，部分动态特性受限

### 方案 B：批处理推理
- 优势：GPU 利用率提升 2–3x
- 劣势：增加延迟，内存占用更高

### 方案 C：Celery 分布式任务队列
- 优势：支持横向扩展、持久化、重试
- 劣势：需 Redis，架构复杂

---

## 七、风险评估

| 风险         | 概率 | 影响 | 缓解措施 |
|------------|----|----|--------|
| 队列积压     | 中  | 高  | 限制队列大小 + 超时机制 |
| 任务丢失     | 低  | 高  | 使用 Redis 持久化队列 |
| 内存泄漏     | 低  | 中  | 定期清理已完成任务 |
| 事件循环阻塞 | 低  | 高  | 确保使用 `run_in_executor` |

---

## 八、验收标准

### ✅ 功能验收
- [ ] 推理时 `/health` 可正常响应
- [ ] 推理时可提交新任务
- [ ] 推理时可查询任务状态
- [ ] 多个任务串行处理，不重复加载模型
- [ ] 任务失败时正确记录错误信息

### ✅ 性能验收
- [ ] HTTP 响应时间 < 100ms
- [ ] 模型仅加载 1 次
- [ ] 内存占用与原方案相同
- [ ] 队列长度可监控

---

## 九、参考资料

- [FastAPI 后台任务文档](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [asyncio 官方文档](https://docs.python.org/3/library/asyncio.html)
- [run_in_executor 用法](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor)

---

## 十、总结

### ✅ 核心价值
1. 解决 HTTP 阻塞问题：推理时服务器仍可响应
2. 资源占用最优：单模型实例，避免重复加载
3. 实施成本低：2–4 小时快速上线
4. 架构简单：无需额外依赖（Redis/Celery）
5. 适合本地部署：单 GPU/CPU 环境最优方案

### 🚀 下一步行动
- 按照 Phase 1 实施代码修改
- 执行测试用例验证功能
- 根据负载调整队列容量
- 监控性能指标，必要时迁移到 Celery

---

- **作者**：Claude Code  
- **审核**：待审核  
- **状态**：待实施  

✅ 本文档已优化，适用于开发评审、CI/CD 配置与团队协作。  
如需导出 PDF / HTML，也可继续协助。
