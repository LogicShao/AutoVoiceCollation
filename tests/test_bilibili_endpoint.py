import os
import time

import pytest
import requests

from config import LLM_SERVER, LLM_SERVER_SUPPORTED

BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')
# Default timeout for waiting task completion (seconds); can be overridden via env
TIMEOUT = int(os.getenv('TEST_BILIBILI_TIMEOUT', '600'))
POLL_INTERVAL = 5

VIDEO_URL = "https://www.bilibili.com/video/BV1wP411W7pe?t=0.3"


@pytest.mark.integration
def test_process_bilibili_endpoint_end_to_end():
    """提交 B 站视频处理请求到 /api/v1/process/bilibili 并轮询直到完成（或超时）。

    要求：
    - 本地 API 服务在 BASE_URL 上可用（默认 http://127.0.0.1:8000）
    - 测试默认使用 text_only=true 来加速处理并避免生成大型二进制文件

    可调整：
    - 设置环境变量 API_BASE_URL 指向不同地址
    - 设置 TEST_BILIBILI_TIMEOUT 来增加等待超时
    """
    # 检查服务是否可达
    h = None
    try:
        h = requests.get(f"{BASE_URL}/health", timeout=5)
    except requests.RequestException as e:
        pytest.skip(f"API not reachable at {BASE_URL}: {e}")

    assert h is not None and h.status_code == 200, f"Health check failed: {getattr(h, 'status_code', None)}"

    # choose a supported llm_api: prefer configured LLM_SERVER if valid, else pick the first supported
    chosen_llm = LLM_SERVER if LLM_SERVER in LLM_SERVER_SUPPORTED else (
        LLM_SERVER_SUPPORTED[0] if LLM_SERVER_SUPPORTED else "")
    payload = {
        "video_url": VIDEO_URL,
        "llm_api": chosen_llm,
        "temperature": 0.1,
        "max_tokens": 6000,
        "text_only": True,
    }

    if not chosen_llm:
        pytest.skip("No supported LLM server configured; skipping integration test")

    # POST the processing request with retries and a longer read timeout.
    post_retries = 3
    resp = None
    for attempt in range(1, post_retries + 1):
        try:
            # timeout=(connect_timeout, read_timeout)
            resp = requests.post(f"{BASE_URL}/api/v1/process/bilibili", json=payload, timeout=(5, 120))
            break
        except requests.exceptions.ReadTimeout as e:
            print(f"POST attempt {attempt} read timeout: {e}")
            if attempt == post_retries:
                pytest.fail(f"POST request read timed out after {post_retries} attempts: {e}")
            time.sleep(2)
            continue
        except requests.exceptions.RequestException as e:
            print(f"POST attempt {attempt} request exception: {e}")
            if attempt == post_retries:
                pytest.fail(f"POST request failed after {post_retries} attempts: {e}")
            time.sleep(2)
            continue

    assert resp is not None, "No response from POST request"
    assert resp.status_code == 200, f"Process request failed: {resp.status_code} {resp.text}"
    try:
        data = resp.json()
    except Exception as e:
        pytest.fail(f"Failed to parse JSON from process response: {e} - body: {getattr(resp, 'text', None)}")
    task_id = data.get('task_id')
    assert task_id, f"No task_id returned: {data}"

    # 轮询任务状态
    elapsed = 0
    status = None
    result = None
    while elapsed < TIMEOUT:
        try:
            r = requests.get(f"{BASE_URL}/api/v1/task/{task_id}", timeout=(5, 30))
            if r.status_code != 200:
                print(f"Warning: got status {r.status_code} when polling task: {r.text}")
                time.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL
                continue
            j = r.json()
        except requests.exceptions.ReadTimeout as e:
            print(f"Polling read timeout, elapsed={elapsed}s: {e}")
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            continue
        except requests.exceptions.RequestException as e:
            print(f"Polling request exception, elapsed={elapsed}s: {e}")
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            continue

        status = j.get('status')
        if status == 'completed':
            result = j.get('result')
            break
        if status == 'failed':
            pytest.fail(f"Task failed: {j.get('message')}")
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    assert status == 'completed', f"Task did not complete within {TIMEOUT}s, last status: {status}"
    assert isinstance(result, dict), "Result should be a dict"

    # 验证输出文件或目录中包含文本结果
    output_dir = result.get('output_dir')
    zip_file = result.get('zip_file')

    def _load_json_if_exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                return __import__('json').load(fh)
        except Exception:
            return None

    text_found = None
    # 首先查看 zip_file（后端在 text_only 模式下会把 json 路径放到 zip_file 字段）
    if zip_file:
        # 如果是本地路径，尝试读取
        if os.path.exists(zip_file):
            if zip_file.lower().endswith('.json'):
                j = _load_json_if_exists(zip_file)
                if j:
                    text_found = j.get('polished_text') or j.get('text') or j.get('audio_text')
            elif zip_file.lower().endswith('.zip'):
                # zip 存在即可视为成功（不解压）
                text_found = True
    # 如果未在 zip_file 中找到文本，尝试在 output_dir 中查找常见文件
    if not text_found and output_dir and os.path.exists(output_dir):
        # 常见文件名
        candidates = [
            os.path.join(output_dir, 'result.json'),
            os.path.join(output_dir, 'polish_text.txt'),
            os.path.join(output_dir, 'polished_text.txt'),
            os.path.join(output_dir, 'audio_transcription.txt'),
            os.path.join(output_dir, 'polish_text.md'),
        ]
        for p in candidates:
            if os.path.exists(p):
                if p.lower().endswith('.json'):
                    j = _load_json_if_exists(p)
                    if j:
                        text_found = j.get('polished_text') or j.get('text') or j.get('audio_text')
                        if text_found:
                            break
                else:
                    try:
                        with open(p, 'r', encoding='utf-8') as fh:
                            txt = fh.read().strip()
                            if txt:
                                text_found = txt
                                break
                    except Exception:
                        continue

    assert text_found, f"Expected textual result in task result or output files, got: {result}"
    # 如果找到了文本并且是字符串，打印片段便于调试
    if isinstance(text_found, str):
        print('\n--- Sample text snippet ---\n', text_found[:300])
