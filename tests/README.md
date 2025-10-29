# API 测试文档

本目录包含 AutoVoiceCollation API 的单元测试和集成测试。

## 测试结构

```
tests/
├── conftest.py                    # pytest 配置和共享 fixtures
├── test_api.py                    # API 单元测试
└── test_bilibili_endpoint.py      # B站端点集成测试
```

## 安装测试依赖

```bash
pip install -r requirements-test.txt
```

## 运行测试

### 运行所有测试

```bash
pytest
```

### 运行特定测试文件

```bash
pytest tests/test_api.py
```

### 运行特定测试类

```bash
pytest tests/test_api.py::TestRootEndpoints
```

### 运行特定测试函数

```bash
pytest tests/test_api.py::TestRootEndpoints::test_root_endpoint
```

### 运行单元测试（排除集成测试）

```bash
pytest -m "not integration"
```

### 运行集成测试

```bash
pytest -m integration
```

### 带覆盖率报告

```bash
pytest --cov=api --cov=src --cov-report=html --cov-report=term-missing
```

生成的覆盖率报告将保存在 `htmlcov/` 目录中。

### 详细输出

```bash
pytest -v -s
```

## 测试说明

### test_api.py - API 单元测试

使用 FastAPI TestClient 进行单元测试，不依赖外部服务。所有外部依赖（如文件处理、LLM 调用等）都通过 mock 进行模拟。

**测试类：**

- `TestRootEndpoints` - 测试根端点和健康检查
- `TestBilibiliEndpoint` - 测试 B站视频处理端点
- `TestAudioEndpoint` - 测试音频处理端点
- `TestBatchEndpoint` - 测试批量处理端点
- `TestSubtitleEndpoint` - 测试字幕处理端点
- `TestSummarizeEndpoint` - 测试文本总结端点
- `TestTaskStatusEndpoint` - 测试任务状态查询
- `TestDownloadEndpoint` - 测试结果下载
- `TestRequestValidation` - 测试请求参数验证
- `TestBackgroundTasks` - 测试后台任务

**特点：**

- 快速执行（不需要实际的文件处理或 LLM 调用）
- 完全隔离（使用 mock 模拟所有外部依赖）
- 覆盖正常情况和异常情况

### test_bilibili_endpoint.py - 集成测试

端到端集成测试，需要实际的 API 服务运行。

**运行前提：**

1. API 服务必须运行（默认：http://127.0.0.1:8000）
2. 配置有效的 LLM API 密钥

**环境变量：**

- `API_BASE_URL`: API 服务地址（默认：http://127.0.0.1:8000）
- `TEST_BILIBILI_TIMEOUT`: 测试超时时间（默认：600 秒）

**运行集成测试：**

```bash
# 启动 API 服务
python api.py

# 在另一个终端运行测试
pytest -m integration
```

## Mock 使用说明

测试使用 `unittest.mock` 进行依赖模拟：

```python
@patch("api.bilibili_video_download_process")
def test_process_bilibili_video_success(self, mock_process, client):
    # 配置 mock 返回值
    mock_process.return_value = ("/output/dir", 10.5, 5.2, "/output/result.zip")

    # 执行测试...
```

## 测试覆盖的功能

### API 端点

- ✅ GET `/` - 根端点
- ✅ GET `/health` - 健康检查
- ✅ POST `/api/v1/process/bilibili` - B站视频处理
- ✅ POST `/api/v1/process/audio` - 音频处理
- ✅ POST `/api/v1/process/batch` - 批量处理
- ✅ POST `/api/v1/process/subtitle` - 字幕处理
- ✅ POST `/api/v1/summarize` - 文本总结
- ✅ GET `/api/v1/task/{task_id}` - 任务状态查询
- ✅ GET `/api/v1/download/{task_id}` - 结果下载

### 功能特性

- ✅ 文件上传验证
- ✅ 参数验证
- ✅ 错误处理
- ✅ 后台任务处理
- ✅ 文本总结功能（新增）
- ✅ summarize 参数支持

### 异常情况

- ✅ 不支持的文件格式
- ✅ 缺少必需参数
- ✅ 无效的参数值
- ✅ 任务不存在
- ✅ 文件不存在
- ✅ 处理失败

## 持续集成

可以在 CI/CD 流程中运行测试：

```yaml
# .github/workflows/test.yml 示例
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run unit tests
        run: pytest -m "not integration" --cov=api --cov=src
```

## 调试测试

### 在测试中使用断点

```python
def test_something(client):
    response = client.get("/")
    import pdb; pdb.set_trace()  # 添加断点
    assert response.status_code == 200
```

### 查看 print 输出

```bash
pytest -s
```

### 只运行失败的测试

```bash
pytest --lf  # last-failed
```

### 调试第一个失败的测试

```bash
pytest -x --pdb  # 在第一个失败时进入调试器
```

## 常见问题

### 测试失败：ModuleNotFoundError

确保项目根目录在 Python 路径中，或使用 pytest 发现机制：

```bash
pytest tests/
```

### 异步测试失败

确保安装了 pytest-asyncio：

```bash
pip install pytest-asyncio
```

### Mock 不生效

确认 mock 的导入路径正确：

```python
# 错误：mock 定义位置
@patch("src.core_process.upload_audio")

# 正确：mock 使用位置
@patch("api.upload_audio")
```

## 贡献指南

添加新测试时：

1. 遵循现有的测试结构和命名约定
2. 使用适当的 fixtures
3. Mock 所有外部依赖
4. 测试正常情况和异常情况
5. 添加清晰的测试文档
6. 确保测试可以独立运行

## 参考资料

- [pytest 文档](https://docs.pytest.org/)
- [FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)
- [unittest.mock 文档](https://docs.python.org/3/library/unittest.mock.html)
