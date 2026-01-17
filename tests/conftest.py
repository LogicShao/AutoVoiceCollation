"""
pytest 配置文件
提供测试所需的 fixtures 和配置
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Set environment variables BEFORE any imports that use them
# This ensures config.py reads the correct values when imported
if "TEMP_DIR" not in os.environ:
    test_temp_dir = Path(tempfile.gettempdir()) / "autovoicecollation_test_temp"
    test_output_dir = Path(tempfile.gettempdir()) / "autovoicecollation_test_output"
    test_temp_dir.mkdir(parents=True, exist_ok=True)
    test_output_dir.mkdir(parents=True, exist_ok=True)

    os.environ["TEMP_DIR"] = str(test_temp_dir)
    os.environ["OUTPUT_DIR"] = str(test_output_dir)
    os.environ["DEEPSEEK_API_KEY"] = "test_deepseek_key"
    os.environ["GEMINI_API_KEY"] = "test_gemini_key"
    os.environ["CEREBRAS_API_KEY"] = "test_cerebras_key"
    os.environ["DASHSCOPE_API_KEY"] = "test_dashscope_key"


# Create a fake font file for testing to avoid font loading errors
# This must be done before any imports that try to load fonts
fake_font_path = Path(__file__).parent / "fake_font.ttf"
if not fake_font_path.exists():
    # Create a minimal fake font file (just a few bytes to make it exist)
    fake_font_path.write_bytes(b"FAKE_FONT_DATA")
os.environ["CHINESE_FONT_PATH"] = str(fake_font_path)


# Create a recursive mock that auto-creates submodules
class RecursiveMock(MagicMock):
    """A MagicMock that returns itself for any attribute access, simulating nested modules"""

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattr__(name)
        return RecursiveMock()


# Mock heavy dependencies before any imports
# This prevents torch, funasr, and other heavy ML libraries from being loaded during tests

# Mock torch and all its submodules recursively
mock_torch = RecursiveMock()
# Configure cuda mock to return proper values for device detection
# Must configure cuda before assigning to mock_torch
mock_cuda = Mock()
mock_cuda.is_available = Mock(return_value=False)
mock_cuda.device_count = Mock(return_value=0)
mock_torch.cuda = mock_cuda
sys.modules["torch"] = mock_torch
sys.modules["torch.nn"] = RecursiveMock()
sys.modules["torch.nn.functional"] = RecursiveMock()

# Mock torchaudio
sys.modules["torchaudio"] = RecursiveMock()

# Mock onnxruntime
mock_onnxruntime = Mock()
mock_onnxruntime.get_available_providers = Mock(return_value=["CPUExecutionProvider"])
sys.modules["onnxruntime"] = mock_onnxruntime

# Mock funasr and all its submodules recursively
mock_funasr = RecursiveMock()
mock_funasr.AutoModel = RecursiveMock()
sys.modules["funasr"] = mock_funasr
sys.modules["funasr.auto"] = RecursiveMock()
sys.modules["funasr.auto.auto_model"] = RecursiveMock()
sys.modules["funasr.losses"] = RecursiveMock()
sys.modules["funasr.losses.label_smoothing_loss"] = RecursiveMock()
sys.modules["funasr.metrics"] = RecursiveMock()
sys.modules["funasr.metrics.compute_acc"] = RecursiveMock()
sys.modules["funasr.models"] = RecursiveMock()
sys.modules["funasr.models.ctc"] = RecursiveMock()
sys.modules["funasr.models.ctc.ctc"] = RecursiveMock()
sys.modules["funasr.register"] = RecursiveMock()
sys.modules["funasr.train_utils"] = RecursiveMock()
sys.modules["funasr.train_utils.device_funcs"] = RecursiveMock()
sys.modules["funasr.utils"] = RecursiveMock()
sys.modules["funasr.utils.datadir_writer"] = RecursiveMock()
sys.modules["funasr.utils.load_utils"] = RecursiveMock()
sys.modules["funasr.utils.torch_function"] = RecursiveMock()

# Mock transformers - must return sample responses for LLM queries
mock_transformers = RecursiveMock()
sys.modules["transformers"] = mock_transformers


# Mock LLM API clients to avoid requiring API keys in CI
# These mocks will make the clients return sample text instead of calling real APIs


# Mock OpenAI client (used for DeepSeek and Qwen)
class MockChatCompletion:
    def __init__(self, content="This is a mocked LLM response."):
        self.content = content


class MockMessage:
    def __init__(self, content="This is a mocked LLM response."):
        self.content = content


class MockChoice:
    def __init__(self, content="This is a mocked LLM response."):
        self.message = MockMessage(content)


class MockCompletionResponse:
    def __init__(self, content="This is a mocked LLM response."):
        self.choices = [MockChoice(content)]


class MockChatCompletions:
    def create(self, **kwargs):
        # Return a mock response
        return MockCompletionResponse()


class MockChat:
    def __init__(self):
        self.completions = MockChatCompletions()


class MockOpenAIClient:
    def __init__(self, api_key=None, base_url=None):
        self.chat = MockChat()


# Replace the OpenAI module before it's imported
sys.modules["openai"] = Mock()
sys.modules["openai"].OpenAI = MockOpenAIClient


# Mock Cerebras client
class MockCerebrasResponse:
    def __init__(self):
        self.choices = [MockChoice("This is a mocked Cerebras response.")]


class MockCerebrasChatCompletions:
    def create(self, **kwargs):
        return MockCerebrasResponse()


class MockCerebrasChat:
    def __init__(self):
        self.completions = MockCerebrasChatCompletions()


class MockCerebrasClient:
    def __init__(self, api_key=None):
        self.chat = MockCerebrasChat()


mock_cerebras = Mock()
mock_cerebras.cloud = Mock()
mock_cerebras.cloud.sdk = Mock()
mock_cerebras.cloud.sdk.Cerebras = MockCerebrasClient
sys.modules["cerebras"] = mock_cerebras
sys.modules["cerebras.cloud"] = mock_cerebras.cloud
sys.modules["cerebras.cloud.sdk"] = mock_cerebras.cloud.sdk


# Mock Google GenAI client
class MockGenAIResponse:
    def __init__(self):
        self.text = "This is a mocked Google GenAI response."


class MockGenAIModels:
    def generate_content(self, **kwargs):
        return MockGenAIResponse()


class MockGenAIClient:
    def __init__(self, api_key=None):
        self.models = MockGenAIModels()


mock_google = Mock()
mock_google.genai = Mock()
mock_google.genai.Client = MockGenAIClient
mock_google.genai.types = Mock()
mock_google.genai.types.GenerateContentConfig = lambda **kwargs: kwargs

sys.modules["google"] = mock_google
sys.modules["google.genai"] = mock_google.genai
sys.modules["google.genai.types"] = mock_google.genai.types


# Mock reportlab and PIL font loading to avoid needing Chinese fonts in CI
# This prevents FileNotFoundError when text_exporter module tries to load fonts on import


# Create a completely non-functional but callable TTFont mock
class MockTTFont:
    """Mock TTFont that doesn't try to read/parse any files"""

    def __init__(self, name, filename):
        self.name = name
        self.filename = filename
        # Don't do anything - avoid reading the file

    def __repr__(self):
        return f"MockTTFont('{self.name}')"


# Mock reportlab font registration
mock_reportlab_pdfmetrics = Mock()
mock_reportlab_pdfmetrics.registerFont = Mock()
mock_reportlab_fonts = Mock()
mock_reportlab_fonts.addMapping = Mock()
mock_reportlab_ttfonts = Mock()
mock_reportlab_ttfonts.TTFont = MockTTFont

# We need to mock before reportlab gets imported
sys.modules["reportlab.pdfbase"] = Mock()
sys.modules["reportlab.pdfbase.pdfmetrics"] = mock_reportlab_pdfmetrics
sys.modules["reportlab.pdfbase.ttfonts"] = mock_reportlab_ttfonts
sys.modules["reportlab.lib.fonts"] = mock_reportlab_fonts


# Mock requests module for DeepSeek API calls
@pytest.fixture(autouse=True)
def mock_requests_post(monkeypatch, request):
    """Mock requests.post to return sample responses for LLM API calls."""
    if request.node.get_closest_marker("integration"):
        return
    import requests

    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code
            self.text = str(json_data)

        def json(self):
            return self.json_data

    def mock_post(*args, **kwargs):
        # Return a mock LLM response
        return MockResponse(
            {"choices": [{"message": {"content": "This is a mocked DeepSeek API response."}}]}
        )

    monkeypatch.setattr(requests, "post", mock_post)


def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (may require external services)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running test")


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def sample_audio_file(test_data_dir, tmp_path):
    """创建一个示例音频文件"""
    audio_file = tmp_path / "test_audio.mp3"
    audio_file.write_bytes(b"fake audio content")
    return audio_file


@pytest.fixture
def sample_video_file(test_data_dir, tmp_path):
    """创建一个示例视频文件"""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake video content")
    return video_file


@pytest.fixture(autouse=True)
def mock_env_vars():
    """提供测试环境变量的引用"""
    return {
        "TEMP_DIR": os.environ.get("TEMP_DIR"),
        "OUTPUT_DIR": os.environ.get("OUTPUT_DIR"),
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
        "CEREBRAS_API_KEY": os.environ.get("CEREBRAS_API_KEY"),
        "DASHSCOPE_API_KEY": os.environ.get("DASHSCOPE_API_KEY"),
    }


@pytest.fixture
def suppress_logger_output(caplog):
    """抑制 logger 输出"""
    import logging

    caplog.set_level(logging.CRITICAL)
    return caplog


@pytest.fixture(autouse=True)
def log_test_info(request):
    """自动记录每个测试的信息，用于调试 CI 失败"""
    import sys

    test_name = request.node.name
    print(f"\n{'=' * 60}")
    print(f"[TEST] Running: {test_name}")
    print(f"Platform: {sys.platform}")
    print(f"Python: {sys.version}")
    print(f"{'=' * 60}\n")

    yield

    # 如果测试失败，打印额外信息
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        print(f"\n{'=' * 60}")
        print(f"[FAILED] Test: {test_name}")
        print(f"{'=' * 60}\n")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test results for logging"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
