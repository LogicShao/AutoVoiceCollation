from typing import List, Dict, Any

import requests

# 你的 FastAPI 服务器地址
BASE_URL = "http://127.0.0.1:8000"


class ApiClient:
    """
    负责与 FastAPI 后端进行通信的客户端。
    """

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def check_health(self) -> bool:
        """检查后端 API 健康状况"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _post_json(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """通用的 POST JSON 请求方法"""
        response = self.session.post(f"{self.base_url}{endpoint}", json=data)
        response.raise_for_status()
        return response.json()

    def process_bilibili(self, video_url: str, llm_api: str, temp: float, max_tokens: int) -> Dict[str, Any]:
        """提交 B 站视频处理任务"""
        payload = {
            "video_url": video_url,
            "llm_api": llm_api,
            "temperature": temp,
            "max_tokens": max_tokens
        }
        return self._post_json("/api/v1/process/bilibili", payload)

    def process_audio(self, file_path: str, llm_api: str, temp: float, max_tokens: int) -> Dict[str, Any]:
        """提交本地音频文件处理任务"""
        with open(file_path, 'rb') as f:
            files = {'file': (file_path, f, 'audio/mpeg')}  # 假设是mp3，类型可以更通用
            data = {
                "llm_api": llm_api,
                "temperature": str(temp),
                "max_tokens": str(max_tokens)
            }
            response = self.session.post(f"{self.base_url}/api/v1/process/audio", files=files, data=data)
            response.raise_for_status()
            return response.json()

    def process_batch(self, urls: List[str], llm_api: str, temp: float, max_tokens: int) -> Dict[str, Any]:
        """提交批量 B 站视频处理任务"""
        payload = {
            "urls": urls,
            "llm_api": llm_api,
            "temperature": temp,
            "max_tokens": max_tokens
        }
        return self._post_json("/api/v1/process/batch", payload)

    def process_subtitle(self, file_path: str) -> Dict[str, Any]:
        """为本地视频文件生成字幕"""
        with open(file_path, 'rb') as f:
            files = {'file': (file_path, f, 'video/mp4')}
            response = self.session.post(f"{self.base_url}/api/v1/process/subtitle", files=files)
            response.raise_for_status()
            return response.json()

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """查询任务状态"""
        response = self.session.get(f"{self.base_url}/api/v1/task/{task_id}")
        response.raise_for_status()
        return response.json()

    def download_result(self, task_id: str, save_path: str) -> str:
        """下载任务结果"""
        with self.session.get(f"{self.base_url}/api/v1/download/{task_id}", stream=True) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return save_path
