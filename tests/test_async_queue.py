"""
异步推理队列功能测试脚本

测试验证：
1. 推理时 HTTP 响应是否仍然可用
2. 多任务并发提交
3. 任务状态查询

注意：这些是集成测试，需要API服务器运行在 http://127.0.0.1:8000
运行方式：python api.py & pytest tests/test_async_queue.py
"""

import json
import sys
import time

import pytest
import requests

# API 基础URL
BASE_URL = "http://127.0.0.1:8000"


def check_server_available():
    """检查API服务器是否可用"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


# 如果服务器不可用，跳过所有测试
pytestmark = pytest.mark.skipif(
    not check_server_available(),
    reason="API服务器未运行 (http://127.0.0.1:8000)，跳过集成测试",
)


@pytest.mark.integration
def test_health_during_inference():
    """测试1: 推理时健康检查仍可响应"""
    print("\n========== 测试1: 推理时健康检查 ==========")

    # 提交一个任务（不等待完成）
    response = requests.post(
        f"{BASE_URL}/api/v1/process/bilibili",
        json={"video_url": "https://www.bilibili.com/video/BV1xx411c7mD"},
    )

    assert response.status_code == 200, f"任务提交失败: {response.status_code}"

    data = response.json()
    assert "task_id" in data, f"响应缺少task_id字段: {data}"
    task_id = data["task_id"]
    response_time = response.elapsed.total_seconds()

    print(f"✅ 任务已提交: {task_id}")
    print(f"   响应时间: {response_time:.3f}秒")

    # 验证响应时间应该很快（<1秒）
    assert response_time < 1.0, f"任务提交响应时间过长: {response_time}秒"

    # 立即测试健康检查
    health_response = requests.get(f"{BASE_URL}/health")
    health_time = health_response.elapsed.total_seconds()

    assert (
        health_response.status_code == 200
    ), f"健康检查失败: {health_response.status_code}"

    print("✅ 健康检查成功（推理期间仍可响应）")
    print(f"   响应时间: {health_time:.3f}秒")

    # 验证健康检查响应时间应该很快
    assert health_time < 0.1, f"健康检查响应时间过长: {health_time}秒"


@pytest.mark.integration
def test_concurrent_tasks():
    """测试2: 多任务并发提交"""
    print("\n========== 测试2: 多任务并发提交 ==========")

    task_ids = []
    test_urls = [
        "https://www.bilibili.com/video/BV1",
        "https://www.bilibili.com/video/BV2",
        "https://www.bilibili.com/video/BV3",
    ]

    start_time = time.time()
    for i, url in enumerate(test_urls, 1):
        response = requests.post(
            f"{BASE_URL}/api/v1/process/bilibili", json={"video_url": url}
        )

        assert response.status_code == 200, f"任务 {i} 提交失败: {response.status_code}"

        data = response.json()
        assert "task_id" in data, f"响应缺少task_id字段: {data}"
        task_id = data["task_id"]
        task_ids.append(task_id)
        print(f"✅ 任务 {i} 已提交: {task_id}")

    total_time = time.time() - start_time
    avg_time = total_time / len(test_urls)

    print(f"\n📊 总提交时间: {total_time:.3f}秒")
    print(f"   平均响应时间: {avg_time:.3f}秒/任务")

    # 验证并发提交性能
    assert total_time < 1.0, f"并发提交时间过长: {total_time}秒"

    if total_time < 1.0:
        print("✅ 并发提交性能优秀")
    else:
        print("⚠️ 并发提交较慢，可能存在问题")


@pytest.mark.integration
def test_task_status_query():
    """测试3: 任务状态查询"""
    print("\n========== 测试3: 任务状态查询 ==========")

    # 先提交一个任务
    response = requests.post(
        f"{BASE_URL}/api/v1/process/bilibili",
        json={"video_url": "https://www.bilibili.com/video/BV1xx411c7mD"},
    )

    assert response.status_code == 200, f"任务提交失败: {response.status_code}"

    data = response.json()
    assert "task_id" in data, f"响应缺少task_id字段: {data}"
    task_id = data["task_id"]
    print(f"✅ 测试任务已提交: {task_id}")

    # 查询任务状态（最多5次，增加等待时间）
    valid_statuses = ["pending", "processing", "completed", "failed", "cancelled"]
    status_query_success = False

    for i in range(5):
        response = requests.get(f"{BASE_URL}/api/v1/task/{task_id}")

        assert response.status_code == 200, f"状态查询失败: {response.status_code}"

        task_info = response.json()
        print(f"\n查询 {i + 1}:")
        print(f"  状态: {task_info['status']}")
        print(f"  消息: {task_info['message']}")
        print(f"  响应时间: {response.elapsed.total_seconds():.3f}秒")

        # 验证状态应该是有效的
        assert (
            task_info["status"] in valid_statuses
        ), f"无效的任务状态: {task_info['status']}"

        # 只要能成功查询到状态（即使是pending），就算成功
        status_query_success = True

        # 如果状态已经变化，说明队列在工作
        if task_info["status"] in ["processing", "completed", "failed"]:
            print(f"✅ 状态已变化，队列正常工作: {task_info['status']}")
            break

        time.sleep(0.5)  # 等待0.5秒后再次查询

    # 验证能够成功查询任务状态（不要求状态变化，因为测试URL可能无效）
    assert status_query_success, "无法查询任务状态"
    print("\n✅ 任务状态查询功能正常")


@pytest.mark.integration
def test_queue_capacity():
    """测试4: 队列状态"""
    print("\n========== 测试4: 队列状态 ==========")

    # 检查队列是否正常工作
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("推理队列运行正常" if sys.stdout.encoding == "utf-8" else "Queue OK")
        assert True
    else:
        # 避免Windows控制台编码问题
        error_msg = "健康检查失败" if sys.stdout.encoding == "utf-8" else "Health check failed"
        print(f"{error_msg}: {response.status_code}")
        assert False, f"健康检查失败: {response.status_code}"
