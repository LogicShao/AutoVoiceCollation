"""
FastAPI 服务接口
提供RESTful API用于与其他程序交互
"""
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import shutil
import os
import uuid
from datetime import datetime

from src.config import *
from src.core_process import (
    upload_audio, bilibili_video_download_process,
    process_multiple_urls, process_subtitles
)

# 创建FastAPI应用
app = FastAPI(
    title="AutoVoiceCollation API",
    description="自动语音识别和文本整理服务API",
    version="1.0.0"
)

# 任务状态存储（简单的内存存储，生产环境应使用数据库）
tasks = {}


# Pydantic模型定义
class BilibiliVideoRequest(BaseModel):
    """B站视频处理请求"""
    video_url: str = Field(..., description="B站视频链接")
    llm_api: str = Field(default=LLM_SERVER, description="LLM服务")
    temperature: float = Field(default=LLM_TEMPERATURE, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=LLM_MAX_TOKENS, gt=0, description="最大token数")


class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    urls: List[str] = Field(..., description="B站视频链接列表")
    llm_api: str = Field(default=LLM_SERVER, description="LLM服务")
    temperature: float = Field(default=LLM_TEMPERATURE, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=LLM_MAX_TOKENS, gt=0, description="最大token数")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, processing, completed, failed")
    message: str = Field(default="", description="消息")
    result: Optional[dict] = Field(default=None, description="处理结果")


class ProcessResult(BaseModel):
    """处理结果"""
    output_dir: str = Field(..., description="输出目录")
    extract_time: float = Field(..., description="提取时间（秒）")
    polish_time: float = Field(..., description="润色时间（秒）")
    zip_file: Optional[str] = Field(default=None, description="ZIP文件路径")


# API端点
@app.get("/")
async def root():
    """根端点，返回API信息"""
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
            "asr_model": ASR_MODEL,
            "llm_server": LLM_SERVER,
            "output_dir": OUTPUT_DIR
        }
    }


@app.post("/api/v1/process/bilibili", response_model=TaskResponse)
async def process_bilibili_video(request: BilibiliVideoRequest, background_tasks: BackgroundTasks):
    """处理B站视频"""
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "pending", "message": "任务已创建"}
    background_tasks.add_task(process_bilibili_task, task_id, request.video_url, request.llm_api, request.temperature, request.max_tokens)
    return TaskResponse(task_id=task_id, status="pending", message="任务已提交，正在处理中")


@app.post("/api/v1/process/audio", response_model=TaskResponse)
async def process_audio_file(file: UploadFile = File(...), llm_api: str = LLM_SERVER, temperature: float = LLM_TEMPERATURE, max_tokens: int = LLM_MAX_TOKENS, background_tasks: BackgroundTasks = None):
    """处理上传的音频文件"""
    allowed_extensions = ['.mp3', '.wav', '.m4a', '.flac']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型。支持的格式: {', '.join(allowed_extensions)}")
    
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "pending", "message": "文件上传中"}
    temp_file_path = os.path.join(TEMP_DIR, f"{task_id}_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        tasks[task_id] = {"status": "failed", "message": f"文件保存失败: {str(e)}"}
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    background_tasks.add_task(process_audio_task, task_id, temp_file_path, llm_api, temperature, max_tokens)
    return TaskResponse(task_id=task_id, status="pending", message="文件已上传，正在处理中")


@app.post("/api/v1/process/batch", response_model=TaskResponse)
async def process_batch_videos(request: BatchProcessRequest, background_tasks: BackgroundTasks):
    """批量处理B站视频"""
    if not request.urls:
        raise HTTPException(status_code=400, detail="URL列表不能为空")
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "pending", "message": "批量任务已创建"}
    urls_text = "\n".join(request.urls)
    background_tasks.add_task(process_batch_task, task_id, urls_text, request.llm_api, request.temperature, request.max_tokens)
    return TaskResponse(task_id=task_id, status="pending", message=f"批量任务已提交，共 {len(request.urls)} 个视频")


@app.post("/api/v1/process/subtitle", response_model=TaskResponse)
async def process_video_subtitle(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """为视频添加字幕"""
    allowed_extensions = ['.mp4', '.avi', '.mkv', '.mov']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式。支持的格式: {', '.join(allowed_extensions)}")
    
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "pending", "message": "视频上传中"}
    temp_file_path = os.path.join(TEMP_DIR, f"{task_id}_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        tasks[task_id] = {"status": "failed", "message": f"文件保存失败: {str(e)}"}
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    background_tasks.add_task(process_subtitle_task, task_id, temp_file_path)
    return TaskResponse(task_id=task_id, status="pending", message="视频已上传，正在生成字幕")


@app.get("/api/v1/task/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """查询任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    task_info = tasks[task_id]
    return TaskResponse(task_id=task_id, status=task_info.get("status", "unknown"), message=task_info.get("message", ""), result=task_info.get("result"))


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
async def process_bilibili_task(task_id: str, video_url: str, llm_api: str, temperature: float, max_tokens: int):
    """后台处理B站视频任务"""
    try:
        tasks[task_id] = {"status": "processing", "message": "正在下载和处理视频"}
        output_dir, extract_time, polish_time, zip_file = bilibili_video_download_process(video_url, llm_api, temperature, max_tokens)
        tasks[task_id] = {"status": "completed", "message": "处理完成", "result": {"output_dir": output_dir, "extract_time": extract_time, "polish_time": polish_time, "zip_file": zip_file}}
    except Exception as e:
        tasks[task_id] = {"status": "failed", "message": f"处理失败: {str(e)}"}


async def process_audio_task(task_id: str, audio_path: str, llm_api: str, temperature: float, max_tokens: int):
    """后台处理音频任务"""
    try:
        tasks[task_id] = {"status": "processing", "message": "正在处理音频"}
        output_dir, extract_time, polish_time, zip_file = upload_audio(audio_path, llm_api, temperature, max_tokens)
        if os.path.exists(audio_path):
            os.remove(audio_path)
        tasks[task_id] = {"status": "completed", "message": "处理完成", "result": {"output_dir": output_dir, "extract_time": extract_time, "polish_time": polish_time, "zip_file": zip_file}}
    except Exception as e:
        tasks[task_id] = {"status": "failed", "message": f"处理失败: {str(e)}"}


async def process_batch_task(task_id: str, urls: str, llm_api: str, temperature: float, max_tokens: int):
    """后台处理批量任务"""
    try:
        tasks[task_id] = {"status": "processing", "message": "正在批量处理视频"}
        result_text, extract_time, polish_time, _, _, _ = process_multiple_urls(urls, llm_api, temperature, max_tokens)
        tasks[task_id] = {"status": "completed", "message": "批量处理完成", "result": {"output_files": result_text, "total_extract_time": extract_time, "total_polish_time": polish_time}}
    except Exception as e:
        tasks[task_id] = {"status": "failed", "message": f"处理失败: {str(e)}"}


async def process_subtitle_task(task_id: str, video_path: str):
    """后台处理字幕任务"""
    try:
        tasks[task_id] = {"status": "processing", "message": "正在生成字幕"}
        srt_file, output_file = process_subtitles(video_path)
        if os.path.exists(video_path):
            os.remove(video_path)
        tasks[task_id] = {"status": "completed", "message": "字幕生成完成", "result": {"srt_file": srt_file, "output_video": output_file}}
    except Exception as e:
        tasks[task_id] = {"status": "failed", "message": f"处理失败: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    port = WEB_SEVER_PORT if WEB_SEVER_PORT else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
