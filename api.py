"""
FastAPI 服务接口
提供RESTful API用于与其他程序交互
"""

import asyncio
import os
import shutil
import socket
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from src.utils.config import get_config
from src.utils.helpers.task_manager import get_task_manager
from src.utils.logging.logger import get_logger


def _import_log(message: str) -> None:
    if os.getenv("AVC_IMPORT_LOG"):
        print(f"[import] {message}", file=sys.stderr, flush=True)


# 创建logger
_import_log("initializing logger")
logger = get_logger(__name__)

# 获取配置
_import_log("loading config")
config = get_config()
_import_log("config loaded")


task_manager = get_task_manager()
_inference_queue = None
_static_files_cls = None
_exception_handlers_registered = False


def _get_inference_queue():
    global _inference_queue
    if _inference_queue is None:
        from src.api.inference_queue import get_inference_queue as _load_inference_queue

        _inference_queue = _load_inference_queue()
    return _inference_queue


def _get_static_files():
    global _static_files_cls
    if _static_files_cls is None:
        from fastapi.staticfiles import StaticFiles as _StaticFiles

        _static_files_cls = _StaticFiles
    return _static_files_cls


def _register_exception_handlers(app: FastAPI):
    global _exception_handlers_registered
    if _exception_handlers_registered:
        return
    from src.api.middleware import register_exception_handlers

    register_exception_handlers(app)

    _exception_handlers_registered = True


class _LazyProcessorProxy:
    def __init__(self, loader, method_names):
        self._loader = loader
        self._instance = None
        for name in method_names:
            setattr(self, name, self._make_proxy(name))

    def _make_proxy(self, name):
        def _proxy(*args, **kwargs):
            return getattr(self._load(), name)(*args, **kwargs)

        return _proxy

    def _load(self):
        if self._instance is None:
            self._instance = self._loader()
        return self._instance

    def __getattr__(self, name):
        return getattr(self._load(), name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期事件处理"""
    logger.info("启动 FastAPI 服务...")
    _register_exception_handlers(app)
    inference_queue = _get_inference_queue()
    await inference_queue.start()
    logger.info("推理队列已启动")
    try:
        yield
    finally:
        logger.info("关闭 FastAPI 服务...")
        await inference_queue.stop()
        logger.info("推理队列已停止")


# 创建FastAPI应用
_import_log("creating FastAPI app")
app = FastAPI(
    title="AutoVoiceCollation API",
    description="自动语音识别和文本整理服务API",
    version="1.0.0",
    lifespan=lifespan,
)
_import_log("FastAPI app created")

# 注册统一异常处理器
_register_exception_handlers(app)

# 挂载静态文件目录（仅当目录存在时）
# 这样可以让测试环境和未构建前端的开发环境也能正常运行
if Path("frontend/dist").exists():
    StaticFiles = _get_static_files()
    app.mount("/dist", StaticFiles(directory="frontend/dist"), name="dist")
    logger.info("已挂载静态文件目录: /dist")
else:
    logger.warning("前端构建目录 'frontend/dist' 不存在，跳过挂载")

if Path("frontend/src").exists():
    StaticFiles = _get_static_files()
    app.mount("/src", StaticFiles(directory="frontend/src"), name="src")
    logger.info("已挂载静态文件目录: /src")

if Path("assets").exists():
    StaticFiles = _get_static_files()
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")
    logger.info("已挂载静态文件目录: /assets")

# 任务状态存储（简单的内存存储，生产环境应使用数据库）
# 每个任务的结构：
# {
#     "status": "pending/processing/completed/failed",
#     "message": "消息",
#     "result": {...},
#     "created_at": "创建时间",
#     "completed_at": "完成时间（可选）",
#     "url": "处理的URL（如果有）",
#     "filename": "处理的文件名（如果有）"
# }
tasks = {}


def _load_video_processor():
    from src.core.processors.video import VideoProcessor

    return VideoProcessor()


def _load_audio_processor():
    from src.core.processors.audio import AudioProcessor

    return AudioProcessor()


def _load_subtitle_processor():
    from src.core.processors.subtitle import SubtitleProcessor

    return SubtitleProcessor()


video_processor = _LazyProcessorProxy(_load_video_processor, ["process", "process_batch"])
audio_processor = _LazyProcessorProxy(_load_audio_processor, ["process_uploaded_audio"])
subtitle_processor = _LazyProcessorProxy(_load_subtitle_processor, ["process", "process_simple"])


def summarize_text(
    txt: str, api_server: str, temperature: float, max_tokens: int, title: str = ""
) -> str:
    from src.text_arrangement.summary_by_llm import summarize_text as _summarize_text

    return _summarize_text(
        txt=txt,
        api_server=api_server,
        temperature=temperature,
        max_tokens=max_tokens,
        title=title,
    )


# Pydantic模型定义
class SummarizeRequest(BaseModel):
    """文本总结请求"""

    text: str = Field(..., description="要总结的文本内容")
    title: str = Field(default="", description="文本标题（可选）")
    llm_api: str = Field(default=config.llm.llm_server, description="LLM服务")
    temperature: float = Field(
        default=config.llm.llm_temperature, ge=0, le=2, description="温度参数"
    )
    max_tokens: int = Field(default=config.llm.llm_max_tokens, gt=0, description="最大token数")


class BilibiliVideoRequest(BaseModel):
    """B站视频处理请求"""

    video_url: str = Field(..., description="B站视频链接")
    llm_api: str = Field(default=config.llm.llm_server, description="LLM服务")
    temperature: float = Field(
        default=config.llm.llm_temperature, ge=0, le=2, description="温度参数"
    )
    max_tokens: int = Field(default=config.llm.llm_max_tokens, gt=0, description="最大token数")
    text_only: bool = Field(default=False, description="仅返回文本结果（不生成PDF）")
    summarize: bool = Field(default=False, description="是否对结果进行总结")


class BatchProcessRequest(BaseModel):
    """批量处理请求"""

    urls: list[str] = Field(..., description="B站视频链接列表")
    llm_api: str = Field(default=config.llm.llm_server, description="LLM服务")
    temperature: float = Field(
        default=config.llm.llm_temperature, ge=0, le=2, description="温度参数"
    )
    max_tokens: int = Field(default=config.llm.llm_max_tokens, gt=0, description="最大token数")
    text_only: bool = Field(default=False, description="仅返回文本结果（不生成PDF）")
    summarize: bool = Field(default=False, description="是否对结果进行总结")


class MultiPartVideoRequest(BaseModel):
    """多P视频处理请求"""

    video_url: str = Field(..., description="B站视频链接")
    selected_parts: list[int] = Field(..., description="选中的分P编号列表（从1开始）", min_length=1)
    llm_api: str = Field(default=config.llm.llm_server, description="LLM服务")
    temperature: float = Field(
        default=config.llm.llm_temperature, ge=0, le=2, description="温度参数"
    )
    max_tokens: int = Field(default=config.llm.llm_max_tokens, gt=0, description="最大token数")
    text_only: bool = Field(default=False, description="仅返回文本结果（不生成PDF）")


class TaskResponse(BaseModel):
    """任务响应"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, processing, completed, failed")
    message: str = Field(default="", description="消息")
    result: dict | None = Field(default=None, description="处理结果")
    error: str | None = Field(default=None, description="错误信息")
    created_at: str | None = Field(default=None, description="任务创建时间（ISO格式）")
    completed_at: str | None = Field(default=None, description="任务完成时间（ISO格式）")
    url: str | None = Field(default=None, description="处理的URL（如果有）")
    filename: str | None = Field(default=None, description="处理的文件名（如果有）")


class TaskListResponse(BaseModel):
    """任务列表响应"""

    tasks: list[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="任务总数")


class ProcessResult(BaseModel):
    """处理结果"""

    output_dir: str = Field(..., description="输出目录")
    extract_time: float = Field(..., description="提取时间（秒）")
    polish_time: float = Field(..., description="润色时间（秒）")
    zip_file: str | None = Field(default=None, description="ZIP文件路径")


# API端点
@app.get("/", response_class=HTMLResponse)
async def root():
    """根端点，返回前端页面"""
    try:
        with open("frontend/src/index.html", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>前端文件未找到</h1><p>请先运行 <code>npm run build</code> 构建前端资源</p>",
            status_code=500,
        )


@app.get("/api")
async def api_info():
    """API信息端点"""
    return {
        "name": "AutoVoiceCollation API",
        "version": "1.0.0",
        "description": "自动语音识别和文本整理服务",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "process_bilibili": "/api/v1/process/bilibili",
            "process_audio": "/api/v1/process/audio",
            "process_batch": "/api/v1/process/batch",
            "process_subtitle": "/api/v1/process/subtitle",
            "summarize": "/api/v1/summarize",
            "task_status": "/api/v1/task/{task_id}",
            "task_list": "/api/v1/tasks",
            "cancel_task": "/api/v1/task/{task_id}/cancel",
            "download_result": "/api/v1/download/{task_id}",
        },
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "asr_model": config.asr.asr_model,
            "llm_server": config.llm.llm_server,
            "output_dir": str(config.paths.output_dir),
        },
    }


@app.post("/api/v1/process/bilibili", response_model=TaskResponse)
async def process_bilibili_video(request: BilibiliVideoRequest):
    """处理B站视频（异步队列版本）"""
    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    # 创建任务记录
    tasks[task_id] = {
        "status": "pending",
        "message": "任务已提交，等待处理",
        "created_at": created_at,
        "url": request.video_url,
        "filename": None,
    }

    # ✅ 提交任务到异步队列（立即返回）
    inference_queue = _get_inference_queue()
    await inference_queue.submit_task(
        task_id=task_id,
        task_type="bilibili",
        task_data={
            "video_url": request.video_url,
            "llm_api": request.llm_api,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "text_only": request.text_only,
            "summarize": request.summarize,
        },
        tasks_store=tasks,  # 引用传递，队列可直接更新状态
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="任务已提交到队列，正在等待处理",
        created_at=created_at,
        url=request.video_url,
    )


async def process_bilibili_task(
    task_id: str,
    video_url: str,
    llm_api: str,
    temperature: float,
    max_tokens: int,
    text_only: bool,
    summarize: bool,
):
    def _extract_output_dir(output_data):
        if isinstance(output_data, dict):
            return output_data.get("output_dir", "")
        return output_data or ""

    task_info = tasks.get(task_id)
    if task_info is None:
        tasks[task_id] = {"status": "pending", "created_at": datetime.now().isoformat()}
        task_info = tasks[task_id]

    task_info.update({"status": "processing", "message": "任务处理中"})

    loop = asyncio.get_running_loop()
    try:
        output_data, extract_time, polish_time, zip_file = await loop.run_in_executor(
            None,
            video_processor.process,
            video_url,
            llm_api,
            temperature,
            max_tokens,
            text_only,
            task_id,
        )
        completed_at = datetime.now().isoformat()

        if text_only:
            result_data = output_data

            if summarize and isinstance(result_data, dict) and "polished_text" in result_data:
                summary = await loop.run_in_executor(
                    None,
                    summarize_text,
                    result_data["polished_text"],
                    llm_api,
                    temperature,
                    max_tokens,
                    result_data.get("title", ""),
                )
                result_data["summary"] = summary
                completed_at = datetime.now().isoformat()

            output_dir = _extract_output_dir(result_data)
            if isinstance(result_data, dict) and output_dir and not result_data.get("zip_file"):
                result_data["zip_file"] = build_lazy_zip_path(task_id, output_dir)

            tasks[task_id].update(
                {
                    "status": "completed",
                    "message": "处理完成",
                    "result": result_data,
                    "completed_at": completed_at,
                }
            )
        else:
            output_dir = _extract_output_dir(output_data)
            zip_file_path = zip_file or build_lazy_zip_path(task_id, output_dir)
            tasks[task_id].update(
                {
                    "status": "completed",
                    "message": "处理完成",
                    "result": {
                        "output_dir": output_dir,
                        "extract_time": extract_time,
                        "polish_time": polish_time,
                        "zip_file": zip_file_path,
                    },
                    "completed_at": completed_at,
                }
            )
    except Exception as e:
        tasks[task_id].update(
            {
                "status": "failed",
                "message": f"处理错误: {str(e)}",
                "error": str(e),
                "completed_at": datetime.now().isoformat(),
            }
        )


@app.post("/api/v1/bilibili/check-multipart")
async def check_multi_part(request: BilibiliVideoRequest):
    """检查B站视频是否为多P"""
    try:
        video_url = request.video_url
        logger.info(f"检查多P视频：{video_url}")

        from src.services.download.bilibili_downloader import get_multi_part_info

        multi_part_info = get_multi_part_info(video_url)

        if multi_part_info is None:
            return {"is_multipart": False, "info": None}

        return {
            "is_multipart": True,
            "info": {
                "main_title": multi_part_info.main_title,
                "total_parts": multi_part_info.total_parts,
                "parts": [
                    {
                        "part_number": p.part_number,
                        "title": p.title,
                        "duration": p.duration,
                        "url": p.url,
                    }
                    for p in multi_part_info.parts
                ],
            },
        }
    except Exception as e:
        logger.error(f"检查多P视频失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}") from e


@app.post("/api/v1/process/multipart", response_model=TaskResponse)
async def process_multi_part_video(request: MultiPartVideoRequest):
    """处理多P视频（异步队列版本）"""
    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    # 创建任务记录
    tasks[task_id] = {
        "status": "pending",
        "message": f"多P任务已提交，共 {len(request.selected_parts)} 个分P",
        "created_at": created_at,
        "url": request.video_url,
        "filename": None,
    }

    # 提交任务到异步队列
    inference_queue = _get_inference_queue()
    await inference_queue.submit_task(
        task_id=task_id,
        task_type="multipart",
        task_data={
            "video_url": request.video_url,
            "selected_parts": request.selected_parts,
            "llm_api": request.llm_api,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "text_only": request.text_only,
        },
        tasks_store=tasks,
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message=f"多P任务已提交，共 {len(request.selected_parts)} 个分P",
        created_at=created_at,
        url=request.video_url,
    )


@app.post("/api/v1/process/audio", response_model=TaskResponse)
async def process_audio_file(
    file: UploadFile = File(...),
    llm_api: str = Form(default=config.llm.llm_server),
    temperature: float = Form(default=config.llm.llm_temperature),
    max_tokens: int = Form(default=config.llm.llm_max_tokens),
    text_only: bool = Form(default=False),
    summarize: bool = Form(default=False),
):
    """处理上传的音频/视频文件（视频会自动提取音频）（异步队列版本）"""
    # 支持音频和视频格式
    audio_extensions = [".mp3", ".wav", ".m4a", ".flac"]
    video_extensions = [".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv"]
    allowed_extensions = audio_extensions + video_extensions

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持的格式: 音频({', '.join(audio_extensions)}) 或 视频({', '.join(video_extensions)})",
        )

    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    # 确定文件类型
    is_video = file_ext in video_extensions

    tasks[task_id] = {
        "status": "pending",
        "message": "视频文件上传中，将自动提取音频" if is_video else "音频文件上传中",
        "created_at": created_at,
        "filename": file.filename,
    }

    # 保存上传的文件到 temp 目录
    temp_file_path = os.path.join(config.paths.temp_dir, f"{task_id}_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "message": f"文件保存失败: {str(e)}",
            "created_at": created_at,
        }
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}") from e

    # 如果是视频文件，提取音频到 download 目录
    if is_video:
        try:
            from src.services.download import extract_audio_from_video

            # 将提取的音频保存到 download 目录
            download_audio_dir = config.paths.download_dir / "extracted_audio"
            download_audio_dir.mkdir(parents=True, exist_ok=True)

            # 提取音频
            audio_path = extract_audio_from_video(
                video_path=temp_file_path,
                output_format="mp3",
                output_dir=str(download_audio_dir),
            )

            # 删除临时视频文件，使用音频文件继续处理
            os.remove(temp_file_path)
            temp_file_path = audio_path

            tasks[task_id]["message"] = "音频提取完成，正在处理"

        except Exception as e:
            tasks[task_id] = {
                "status": "failed",
                "message": f"音频提取失败: {str(e)}",
                "created_at": created_at,
            }
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise HTTPException(status_code=500, detail=f"音频提取失败: {str(e)}") from e

    # ✅ 提交任务到异步队列（立即返回）
    inference_queue = _get_inference_queue()
    await inference_queue.submit_task(
        task_id=task_id,
        task_type="audio",
        task_data={
            "audio_path": temp_file_path,
            "llm_api": llm_api,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "text_only": text_only,
            "summarize": summarize,
        },
        tasks_store=tasks,
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="文件已上传，任务已提交到队列，正在等待处理",
        created_at=created_at,
        filename=file.filename,
    )


@app.post("/api/v1/process/batch", response_model=TaskResponse)
async def process_batch_videos(request: BatchProcessRequest):
    """批量处理B站视频（异步队列版本）"""
    if not request.urls:
        raise HTTPException(status_code=400, detail="URL列表不能为空")

    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    # 创建任务记录
    tasks[task_id] = {
        "status": "pending",
        "message": "批量任务已提交，等待处理",
        "created_at": created_at,
        "url": ", ".join(request.urls),  # 多个URL用逗号分隔
    }

    # 将URL列表转为换行分隔的字符串
    urls_text = "\n".join(request.urls)

    # ✅ 提交任务到异步队列（立即返回）
    inference_queue = _get_inference_queue()
    await inference_queue.submit_task(
        task_id=task_id,
        task_type="batch",
        task_data={
            "urls": urls_text,
            "llm_api": request.llm_api,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "text_only": request.text_only,
            "summarize": request.summarize,
        },
        tasks_store=tasks,
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message=f"批量任务已提交到队列，共 {len(request.urls)} 个视频，正在等待处理",
        created_at=created_at,
        url=", ".join(request.urls),
    )


@app.post("/api/v1/process/subtitle", response_model=TaskResponse)
async def process_video_subtitle(file: UploadFile = File(...)):
    """为视频添加字幕（异步队列版本）"""
    allowed_extensions = [".mp4", ".avi", ".mkv", ".mov"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的视频格式。支持的格式: {', '.join(allowed_extensions)}",
        )

    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    tasks[task_id] = {
        "status": "pending",
        "message": "视频上传中",
        "created_at": created_at,
        "filename": file.filename,
    }

    temp_file_path = os.path.join(config.paths.temp_dir, f"{task_id}_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        tasks[task_id] = {
            "status": "failed",
            "message": f"文件保存失败: {str(e)}",
            "created_at": created_at,
        }
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}") from e

    # ✅ 提交任务到异步队列（立即返回）
    inference_queue = _get_inference_queue()
    await inference_queue.submit_task(
        task_id=task_id,
        task_type="subtitle",
        task_data={"video_path": temp_file_path},
        tasks_store=tasks,
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="视频已上传，任务已提交到队列，正在等待处理",
        created_at=created_at,
        filename=file.filename,
    )


@app.post("/api/v1/summarize")
async def summarize_text_endpoint(request: SummarizeRequest):
    """对文本进行总结"""
    try:
        summary = summarize_text(
            txt=request.text,
            api_server=request.llm_api,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            title=request.title,
        )
        return {
            "status": "success",
            "summary": summary,
            "original_length": len(request.text),
            "summary_length": len(summary),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"总结失败: {str(e)}") from e


@app.get("/api/v1/task/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """查询任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    task_info = tasks[task_id]
    return TaskResponse(
        task_id=task_id,
        status=task_info.get("status", "unknown"),
        message=task_info.get("message", ""),
        result=task_info.get("result"),
        error=task_info.get("error"),
        created_at=task_info.get("created_at"),
        completed_at=task_info.get("completed_at"),
        url=task_info.get("url"),
        filename=task_info.get("filename"),
    )


@app.get("/api/v1/tasks", response_model=TaskListResponse)
async def list_tasks():
    """获取任务列表"""
    task_items = sorted(
        tasks.items(),
        key=lambda item: item[1].get("created_at") or "",
        reverse=True,
    )
    task_list = [
        TaskResponse(
            task_id=task_id,
            status=task_info.get("status", "unknown"),
            message=task_info.get("message", ""),
            result=task_info.get("result"),
            error=task_info.get("error"),
            created_at=task_info.get("created_at"),
            completed_at=task_info.get("completed_at"),
            url=task_info.get("url"),
            filename=task_info.get("filename"),
        )
        for task_id, task_info in task_items
    ]
    return TaskListResponse(tasks=task_list, total=len(task_list))


@app.post("/api/v1/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_info = tasks[task_id]
    status = task_info.get("status", "unknown")

    if status in ("completed", "failed", "cancelled"):
        return {
            "task_id": task_id,
            "status": status,
            "message": "任务已结束，无法取消",
        }

    task_manager.request_cancel(task_id)
    task_info.update(
        {
            "status": "cancelled",
            "message": "任务取消请求已提交",
            "completed_at": datetime.now().isoformat(),
        }
    )

    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "任务取消请求已提交",
    }


def build_lazy_zip_path(task_id: str, output_dir: str) -> str:
    if not output_dir:
        return ""
    safe_name = Path(output_dir).name or "output"
    return str(config.paths.temp_dir / f"{safe_name}_{task_id}.zip")


@app.get("/api/v1/download/{task_id}")
async def download_result(task_id: str):
    """下载处理结果"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    task_info = tasks[task_id]
    if task_info.get("status") != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")
    result = task_info.get("result", {})
    zip_file = result.get("zip_file")
    output_dir = result.get("output_dir")

    if zip_file and os.path.exists(zip_file):
        return FileResponse(
            zip_file, media_type="application/zip", filename=os.path.basename(zip_file)
        )

    if not zip_file:
        if not output_dir:
            raise HTTPException(status_code=404, detail="结果文件不存在")
        zip_file = build_lazy_zip_path(task_id, output_dir)
        result["zip_file"] = zip_file

    if not output_dir or not os.path.isdir(output_dir):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    zip_path = Path(zip_file)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.make_archive(
        base_name=str(zip_path.with_suffix("")),
        format="zip",
        root_dir=output_dir,
    )

    return FileResponse(zip_file, media_type="application/zip", filename=os.path.basename(zip_file))


def is_port_available(host: str, port: int) -> bool:
    """
    检查端口是否可用

    Args:
        host: 主机地址
        port: 端口号

    Returns:
        bool: 端口可用返回 True，否则返回 False
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return True
    except (OSError, PermissionError):
        return False


def find_available_port(host: str, start_port: int, max_attempts: int = 50) -> int:
    """
    查找可用端口

    Args:
        host: 主机地址
        start_port: 起始端口
        max_attempts: 最大尝试次数

    Returns:
        int: 可用的端口号，如果找不到则返回 None
    """
    # 首先尝试指定的起始端口
    if is_port_available(host, start_port):
        return start_port

    print(f"端口 {start_port} 不可用，正在自动寻找可用端口...")

    # 尝试起始端口附近的端口
    for offset in range(1, max_attempts):
        # 先尝试递增
        port = start_port + offset
        if port <= 65535 and is_port_available(host, port):
            print(f"找到可用端口: {port}")
            return port

        # 再尝试递减（如果还在有效范围内）
        port = start_port - offset
        if port >= 1024 and is_port_available(host, port):
            print(f"找到可用端口: {port}")
            return port

    return None


if __name__ == "__main__":
    import uvicorn

    # 获取配置的端口
    preferred_port = config.web_server_port or 8000

    # 主机地址：使用 127.0.0.1 避免 Windows 权限问题
    # 如需外部访问，请以管理员权限运行或使用 host="0.0.0.0"
    host = "127.0.0.1"

    # 查找可用端口
    available_port = find_available_port(host, preferred_port, max_attempts=50)

    if available_port is None:
        print(f"错误: 无法找到可用端口（从 {preferred_port} 开始尝试了 50 个端口）")
        print("请检查防火墙设置或手动指定其他端口")
        exit(1)

    # 提示信息
    if available_port != preferred_port:
        print(f"注意: 配置的端口 {preferred_port} 不可用，已自动切换到端口 {available_port}")

    print("正在启动 AutoVoiceCollation API 服务器...")
    print(f"访问地址: http://{host}:{available_port}")
    print(f"API 文档: http://{host}:{available_port}/docs")
    print(f"健康检查: http://{host}:{available_port}/health")
    print("-" * 60)

    # 启动服务器
    uvicorn.run(app, host=host, port=available_port, access_log=False)
