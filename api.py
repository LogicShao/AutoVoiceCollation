"""
FastAPI 服务接口
提供RESTful API用于与其他程序交互
"""

import os
import shutil
import socket
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.utils.config import get_config
from src.core_process import (
    upload_audio, bilibili_video_download_process,
    process_multiple_urls, process_subtitles
)
from src.text_arrangement.summary_by_llm import summarize_text
from src.api.middleware import register_exception_handlers
from src.utils.logging.logger import get_logger

# 创建logger
logger = get_logger(__name__)

# 获取配置
config = get_config()

# 创建FastAPI应用
app = FastAPI(
    title="AutoVoiceCollation API",
    description="自动语音识别和文本整理服务API",
    version="1.0.0"
)

# 注册统一异常处理器
register_exception_handlers(app)

# 挂载静态文件目录（仅当目录存在时）
# 这样可以让测试环境和未构建前端的开发环境也能正常运行
if Path("frontend/dist").exists():
    app.mount("/dist", StaticFiles(directory="frontend/dist"), name="dist")
    logger.info("已挂载静态文件目录: /dist")
else:
    logger.warning("前端构建目录 'frontend/dist' 不存在，跳过挂载")

if Path("frontend/src").exists():
    app.mount("/src", StaticFiles(directory="frontend/src"), name="src")
    logger.info("已挂载静态文件目录: /src")

if Path("assets").exists():
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


# Pydantic模型定义
class SummarizeRequest(BaseModel):
    """文本总结请求"""
    text: str = Field(..., description="要总结的文本内容")
    title: str = Field(default="", description="文本标题（可选）")
    llm_api: str = Field(default=config.llm.llm_server, description="LLM服务")
    temperature: float = Field(default=config.llm.llm_temperature, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=config.llm.llm_max_tokens, gt=0, description="最大token数")


class BilibiliVideoRequest(BaseModel):
    """B站视频处理请求"""
    video_url: str = Field(..., description="B站视频链接")
    llm_api: str = Field(default=config.llm.llm_server, description="LLM服务")
    temperature: float = Field(default=config.llm.llm_temperature, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=config.llm.llm_max_tokens, gt=0, description="最大token数")
    text_only: bool = Field(default=False, description="仅返回文本结果（不生成PDF）")
    summarize: bool = Field(default=False, description="是否对结果进行总结")


class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    urls: List[str] = Field(..., description="B站视频链接列表")
    llm_api: str = Field(default=config.llm.llm_server, description="LLM服务")
    temperature: float = Field(default=config.llm.llm_temperature, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=config.llm.llm_max_tokens, gt=0, description="最大token数")
    text_only: bool = Field(default=False, description="仅返回文本结果（不生成PDF）")
    summarize: bool = Field(default=False, description="是否对结果进行总结")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, processing, completed, failed")
    message: str = Field(default="", description="消息")
    result: Optional[dict] = Field(default=None, description="处理结果")
    created_at: Optional[str] = Field(default=None, description="任务创建时间（ISO格式）")
    completed_at: Optional[str] = Field(default=None, description="任务完成时间（ISO格式）")
    url: Optional[str] = Field(default=None, description="处理的URL（如果有）")
    filename: Optional[str] = Field(default=None, description="处理的文件名（如果有）")


class ProcessResult(BaseModel):
    """处理结果"""
    output_dir: str = Field(..., description="输出目录")
    extract_time: float = Field(..., description="提取时间（秒）")
    polish_time: float = Field(..., description="润色时间（秒）")
    zip_file: Optional[str] = Field(default=None, description="ZIP文件路径")


# API端点
@app.get("/", response_class=HTMLResponse)
async def root():
    """根端点，返回前端页面"""
    try:
        with open("frontend/src/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>前端文件未找到</h1><p>请先运行 <code>npm run build</code> 构建前端资源</p>",
            status_code=500
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
            "download_result": "/api/v1/download/{task_id}"
        }
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
            "output_dir": str(config.paths.output_dir)
        }
    }


@app.post("/api/v1/process/bilibili", response_model=TaskResponse)
async def process_bilibili_video(request: BilibiliVideoRequest, background_tasks: BackgroundTasks):
    """处理B站视频"""
    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    tasks[task_id] = {
        "status": "pending",
        "message": "任务已创建",
        "created_at": created_at,
        "url": request.video_url
    }
    background_tasks.add_task(process_bilibili_task, task_id, request.video_url, request.llm_api, request.temperature,
                              request.max_tokens, request.text_only, request.summarize)
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="任务已提交，正在处理中",
        created_at=created_at,
        url=request.video_url
    )


@app.post("/api/v1/process/audio", response_model=TaskResponse)
async def process_audio_file(file: UploadFile = File(...), llm_api: str = config.llm.llm_server,
                             temperature: float = config.llm.llm_temperature, max_tokens: int = config.llm.llm_max_tokens,
                             text_only: bool = False, summarize: bool = False,
                             background_tasks: BackgroundTasks = None):
    """处理上传的音频文件"""
    allowed_extensions = ['.mp3', '.wav', '.m4a', '.flac']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型。支持的格式: {', '.join(allowed_extensions)}")

    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    tasks[task_id] = {
        "status": "pending",
        "message": "文件上传中",
        "created_at": created_at,
        "filename": file.filename
    }
    temp_file_path = os.path.join(config.paths.temp_dir, f"{task_id}_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        tasks[task_id] = {"status": "failed", "message": f"文件保存失败: {str(e)}", "created_at": created_at}
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    background_tasks.add_task(process_audio_task, task_id, temp_file_path, llm_api, temperature, max_tokens, text_only,
                              summarize)
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="文件已上传，正在处理中",
        created_at=created_at,
        filename=file.filename
    )


@app.post("/api/v1/process/batch", response_model=TaskResponse)
async def process_batch_videos(request: BatchProcessRequest, background_tasks: BackgroundTasks):
    """批量处理B站视频"""
    if not request.urls:
        raise HTTPException(status_code=400, detail="URL列表不能为空")
    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    tasks[task_id] = {
        "status": "pending",
        "message": "批量任务已创建",
        "created_at": created_at,
        "url": ", ".join(request.urls)  # 多个URL用逗号分隔
    }
    urls_text = "\n".join(request.urls)
    background_tasks.add_task(process_batch_task, task_id, urls_text, request.llm_api, request.temperature,
                              request.max_tokens, request.text_only, request.summarize)
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message=f"批量任务已提交，共 {len(request.urls)} 个视频",
        created_at=created_at,
        url=", ".join(request.urls)
    )


@app.post("/api/v1/process/subtitle", response_model=TaskResponse)
async def process_video_subtitle(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """为视频添加字幕"""
    allowed_extensions = ['.mp4', '.avi', '.mkv', '.mov']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式。支持的格式: {', '.join(allowed_extensions)}")

    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    tasks[task_id] = {
        "status": "pending",
        "message": "视频上传中",
        "created_at": created_at,
        "filename": file.filename
    }
    temp_file_path = os.path.join(config.paths.temp_dir, f"{task_id}_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        tasks[task_id] = {"status": "failed", "message": f"文件保存失败: {str(e)}", "created_at": created_at}
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    background_tasks.add_task(process_subtitle_task, task_id, temp_file_path)
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="视频已上传，正在生成字幕",
        created_at=created_at,
        filename=file.filename
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
            title=request.title
        )
        return {
            "status": "success",
            "summary": summary,
            "original_length": len(request.text),
            "summary_length": len(summary)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"总结失败: {str(e)}")


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
        created_at=task_info.get("created_at"),
        completed_at=task_info.get("completed_at"),
        url=task_info.get("url"),
        filename=task_info.get("filename")
    )


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
    if not zip_file or not os.path.exists(zip_file):
        raise HTTPException(status_code=404, detail="结果文件不存在")
    return FileResponse(zip_file, media_type="application/zip", filename=os.path.basename(zip_file))


# 后台任务处理函数
async def process_bilibili_task(task_id: str, video_url: str, llm_api: str, temperature: float, max_tokens: int,
                                text_only: bool = False, summarize: bool = False):
    """后台处理B站视频任务"""
    try:
        # 更新状态为处理中，保留原有信息
        task_data = tasks[task_id].copy()
        task_data.update({"status": "processing", "message": "正在下载和处理视频"})
        tasks[task_id] = task_data

        output_data, extract_time, polish_time, zip_file = bilibili_video_download_process(video_url, llm_api,
                                                                                           temperature, max_tokens,
                                                                                           text_only)
        completed_at = datetime.now().isoformat()

        if text_only:
            # text_only 模式：返回文本内容
            result_data = output_data  # output_data 是包含文本内容的字典
            # 如果需要总结，对润色后的文本进行总结
            if summarize and "polished_text" in result_data:
                task_data.update({"status": "processing", "message": "正在生成总结"})
                tasks[task_id] = task_data
                summary = summarize_text(
                    txt=result_data["polished_text"],
                    api_server=llm_api,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    title=result_data.get("title", "")
                )
                result_data["summary"] = summary
                completed_at = datetime.now().isoformat()  # 更新完成时间

            task_data.update({
                "status": "completed",
                "message": "处理完成",
                "result": result_data,
                "completed_at": completed_at
            })
            tasks[task_id] = task_data
        else:
            # 正常模式：返回文件路径
            task_data.update({
                "status": "completed",
                "message": "处理完成",
                "result": {
                    "output_dir": output_data,
                    "extract_time": extract_time,
                    "polish_time": polish_time,
                    "zip_file": zip_file
                },
                "completed_at": completed_at
            })
            tasks[task_id] = task_data
    except Exception as e:
        logger.error(f"B站视频处理失败 (task_id={task_id}, url={video_url}): {e}", exc_info=True)
        logger.error(f"完整堆栈:\n{traceback.format_exc()}")

        task_data = tasks[task_id].copy()
        task_data.update({
            "status": "failed",
            "message": f"处理失败: {str(e)}",
            "completed_at": datetime.now().isoformat(),
            "error_detail": str(e) + "\n" + traceback.format_exc()
        })
        tasks[task_id] = task_data


async def process_audio_task(task_id: str, audio_path: str, llm_api: str, temperature: float, max_tokens: int,
                             text_only: bool = False, summarize: bool = False):
    """后台处理音频任务"""
    try:
        # 更新状态为处理中，保留原有信息
        task_data = tasks[task_id].copy()
        task_data.update({"status": "processing", "message": "正在处理音频"})
        tasks[task_id] = task_data

        output_data, extract_time, polish_time, zip_file = upload_audio(audio_path, llm_api, temperature, max_tokens,
                                                                        text_only)
        if os.path.exists(audio_path):
            os.remove(audio_path)

        completed_at = datetime.now().isoformat()

        if text_only:
            # text_only 模式：返回文本内容
            result_data = output_data  # output_data 是包含文本内容的字典
            # 如果需要总结，对润色后的文本进行总结
            if summarize and "polished_text" in result_data:
                task_data.update({"status": "processing", "message": "正在生成总结"})
                tasks[task_id] = task_data
                summary = summarize_text(
                    txt=result_data["polished_text"],
                    api_server=llm_api,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    title=result_data.get("title", "")
                )
                result_data["summary"] = summary
                completed_at = datetime.now().isoformat()  # 更新完成时间

            task_data.update({
                "status": "completed",
                "message": "处理完成",
                "result": result_data,
                "completed_at": completed_at
            })
            tasks[task_id] = task_data
        else:
            # 正常模式：返回文件路径
            task_data.update({
                "status": "completed",
                "message": "处理完成",
                "result": {
                    "output_dir": output_data,
                    "extract_time": extract_time,
                    "polish_time": polish_time,
                    "zip_file": zip_file
                },
                "completed_at": completed_at
            })
            tasks[task_id] = task_data
    except Exception as e:
        task_data = tasks[task_id].copy()
        task_data.update({
            "status": "failed",
            "message": f"处理失败: {str(e)}",
            "completed_at": datetime.now().isoformat()
        })
        tasks[task_id] = task_data


async def process_batch_task(task_id: str, urls: str, llm_api: str, temperature: float, max_tokens: int,
                             text_only: bool = False, summarize: bool = False):
    """后台处理批量任务"""
    try:
        # 更新状态为处理中，保留原有信息
        task_data = tasks[task_id].copy()
        task_data.update({"status": "processing", "message": "正在批量处理视频"})
        tasks[task_id] = task_data

        result_text, extract_time, polish_time, _, _, _ = process_multiple_urls(urls, llm_api, temperature, max_tokens,
                                                                                text_only)
        result_data = {"output_files": result_text, "total_extract_time": extract_time,
                       "total_polish_time": polish_time}

        # 如果需要总结且返回的是文本模式，对每个视频的文本进行总结
        if summarize and text_only and isinstance(result_text, list):
            task_data.update({"status": "processing", "message": "正在生成总结"})
            tasks[task_id] = task_data
            summaries = []
            for item in result_text:
                if isinstance(item, dict) and "polished_text" in item:
                    summary = summarize_text(
                        txt=item["polished_text"],
                        api_server=llm_api,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        title=item.get("title", "")
                    )
                    item["summary"] = summary
                    summaries.append({"title": item.get("title", ""), "summary": summary})
            result_data["summaries"] = summaries

        completed_at = datetime.now().isoformat()
        task_data.update({
            "status": "completed",
            "message": "批量处理完成",
            "result": result_data,
            "completed_at": completed_at
        })
        tasks[task_id] = task_data
    except Exception as e:
        task_data = tasks[task_id].copy()
        task_data.update({
            "status": "failed",
            "message": f"处理失败: {str(e)}",
            "completed_at": datetime.now().isoformat()
        })
        tasks[task_id] = task_data


async def process_subtitle_task(task_id: str, video_path: str):
    """后台处理字幕任务"""
    try:
        # 更新状态为处理中，保留原有信息
        task_data = tasks[task_id].copy()
        task_data.update({"status": "processing", "message": "正在生成字幕"})
        tasks[task_id] = task_data

        srt_file, output_file = process_subtitles(video_path)
        if os.path.exists(video_path):
            os.remove(video_path)

        completed_at = datetime.now().isoformat()
        task_data.update({
            "status": "completed",
            "message": "字幕生成完成",
            "result": {"srt_file": srt_file, "output_video": output_file},
            "completed_at": completed_at
        })
        tasks[task_id] = task_data
    except Exception as e:
        task_data = tasks[task_id].copy()
        task_data.update({
            "status": "failed",
            "message": f"处理失败: {str(e)}",
            "completed_at": datetime.now().isoformat()
        })
        tasks[task_id] = task_data


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

    print(f"正在启动 AutoVoiceCollation API 服务器...")
    print(f"访问地址: http://{host}:{available_port}")
    print(f"API 文档: http://{host}:{available_port}/docs")
    print(f"健康检查: http://{host}:{available_port}/health")
    print("-" * 60)

    # 启动服务器
    uvicorn.run(app, host=host, port=available_port)
