"""
设备检测和管理模块
支持自动检测 CPU/GPU，以及 ONNX Runtime 的执行提供者配置
"""

from typing import List, Optional
import sys

from src.logger import get_logger

logger = get_logger(__name__)


def is_torch_available() -> bool:
    """检查 PyTorch 是否可用"""
    try:
        import torch
        return True
    except ImportError:
        return False


def is_cuda_available() -> bool:
    """检查 CUDA 是否可用"""
    if not is_torch_available():
        return False
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def get_cuda_device_count() -> int:
    """获取 CUDA 设备数量"""
    if not is_cuda_available():
        return 0
    try:
        import torch
        return torch.cuda.device_count()
    except Exception:
        return 0


def is_onnxruntime_available() -> bool:
    """检查 ONNX Runtime 是否可用"""
    try:
        import onnxruntime
        return True
    except ImportError:
        return False


def get_onnxruntime_providers() -> List[str]:
    """获取 ONNX Runtime 可用的执行提供者列表"""
    if not is_onnxruntime_available():
        return []
    try:
        import onnxruntime
        return onnxruntime.get_available_providers()
    except Exception:
        return []


def detect_device(device_config: str = "auto") -> str:
    """
    自动检测或解析设备配置

    Args:
        device_config: 设备配置字符串，可以是:
            - "auto": 自动检测，优先使用 GPU
            - "cpu": 强制使用 CPU
            - "cuda": 使用第一个 CUDA 设备
            - "cuda:0", "cuda:1" 等: 使用指定的 CUDA 设备

    Returns:
        str: 设备字符串 (如 "cpu", "cuda:0")
    """
    device_config = device_config.lower().strip()

    # 如果是 auto，自动检测
    if device_config == "auto":
        if is_cuda_available():
            device = "cuda:0"
            logger.info(f"自动检测到 CUDA 可用，使用设备: {device}")

            # 打印 CUDA 设备信息
            cuda_count = get_cuda_device_count()
            if cuda_count > 0:
                try:
                    import torch
                    logger.info(f"检测到 {cuda_count} 个 CUDA 设备:")
                    for i in range(cuda_count):
                        device_name = torch.cuda.get_device_name(i)
                        logger.info(f"  - CUDA:{i} - {device_name}")
                except Exception as e:
                    logger.warning(f"无法获取 CUDA 设备详细信息: {e}")
        else:
            device = "cpu"
            logger.info("未检测到 CUDA，使用 CPU")

    # 如果是 cpu
    elif device_config == "cpu":
        device = "cpu"
        logger.info("使用 CPU 设备")

    # 如果是 cuda 或 cuda:X 格式
    elif device_config.startswith("cuda"):
        if not is_cuda_available():
            logger.warning(f"配置要求使用 {device_config}，但 CUDA 不可用，回退到 CPU")
            device = "cpu"
        else:
            # 验证设备索引是否有效
            if ":" in device_config:
                try:
                    device_idx = int(device_config.split(":")[1])
                    cuda_count = get_cuda_device_count()
                    if device_idx >= cuda_count:
                        logger.warning(
                            f"配置的 CUDA 设备索引 {device_idx} 超出范围 (共 {cuda_count} 个设备)，使用 cuda:0"
                        )
                        device = "cuda:0"
                    else:
                        device = device_config
                        logger.info(f"使用 CUDA 设备: {device}")
                except ValueError:
                    logger.warning(f"无效的设备配置: {device_config}，使用 cuda:0")
                    device = "cuda:0"
            else:
                device = "cuda:0"
                logger.info(f"使用 CUDA 设备: {device}")

    # 其他情况
    else:
        logger.warning(f"无法识别的设备配置: {device_config}，回退到自动检测")
        return detect_device("auto")

    return device


def get_onnx_providers(
    device: str,
    custom_providers: Optional[str] = None
) -> List[str]:
    """
    根据设备配置和自定义提供者获取 ONNX Runtime 执行提供者

    Args:
        device: 设备字符串 (如 "cpu", "cuda:0")
        custom_providers: 自定义提供者字符串（逗号分隔），如 "CUDAExecutionProvider,CPUExecutionProvider"

    Returns:
        List[str]: ONNX 执行提供者列表
    """
    if not is_onnxruntime_available():
        logger.warning("ONNX Runtime 未安装，无法使用 ONNX 推理")
        return []

    available_providers = get_onnxruntime_providers()
    logger.info(f"ONNX Runtime 可用的执行提供者: {available_providers}")

    # 如果用户指定了自定义提供者
    if custom_providers and custom_providers.strip():
        custom_list = [p.strip() for p in custom_providers.split(",") if p.strip()]
        providers = []
        for provider in custom_list:
            if provider in available_providers:
                providers.append(provider)
                logger.info(f"使用自定义 ONNX 提供者: {provider}")
            else:
                logger.warning(f"自定义 ONNX 提供者 {provider} 不可用，跳过")

        if providers:
            return providers
        else:
            logger.warning("所有自定义 ONNX 提供者均不可用，使用默认配置")

    # 根据设备自动选择提供者
    providers = []

    if device.startswith("cuda"):
        # 优先使用 CUDA
        if "CUDAExecutionProvider" in available_providers:
            providers.append("CUDAExecutionProvider")
            logger.info("使用 ONNX CUDAExecutionProvider")
        elif "TensorrtExecutionProvider" in available_providers:
            providers.append("TensorrtExecutionProvider")
            logger.info("使用 ONNX TensorrtExecutionProvider")
        else:
            logger.warning("未找到 GPU 相关的 ONNX 执行提供者，回退到 CPU")

    # 始终添加 CPU 作为后备
    if "CPUExecutionProvider" in available_providers:
        providers.append("CPUExecutionProvider")
        if device == "cpu":
            logger.info("使用 ONNX CPUExecutionProvider")

    if not providers:
        logger.error("没有可用的 ONNX 执行提供者")
        return available_providers  # 返回所有可用的，让 ONNX Runtime 自己决定

    return providers


def print_device_info():
    """打印系统设备信息（用于调试）"""
    logger.info("=" * 60)
    logger.info("系统设备信息:")
    logger.info(f"Python 版本: {sys.version}")

    # PyTorch 信息
    if is_torch_available():
        import torch
        logger.info(f"PyTorch 版本: {torch.__version__}")
        logger.info(f"CUDA 可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"CUDA 版本: {torch.version.cuda}")
            logger.info(f"cuDNN 版本: {torch.backends.cudnn.version()}")
            cuda_count = torch.cuda.device_count()
            logger.info(f"CUDA 设备数量: {cuda_count}")
            for i in range(cuda_count):
                device_name = torch.cuda.get_device_name(i)
                logger.info(f"  - CUDA:{i} - {device_name}")
    else:
        logger.info("PyTorch 未安装")

    # ONNX Runtime 信息
    if is_onnxruntime_available():
        import onnxruntime
        logger.info(f"ONNX Runtime 版本: {onnxruntime.__version__}")
        providers = onnxruntime.get_available_providers()
        logger.info(f"ONNX 可用执行提供者: {providers}")
    else:
        logger.info("ONNX Runtime 未安装")

    logger.info("=" * 60)


if __name__ == "__main__":
    # 测试代码
    print_device_info()

    # 测试设备检测
    print("\n测试设备检测:")
    for config in ["auto", "cpu", "cuda", "cuda:0", "cuda:1", "invalid"]:
        device = detect_device(config)
        print(f"  配置: {config} -> 设备: {device}")

    # 测试 ONNX 提供者
    print("\n测试 ONNX 提供者:")
    device = detect_device("auto")
    providers = get_onnx_providers(device)
    print(f"  设备 {device} 的 ONNX 提供者: {providers}")
