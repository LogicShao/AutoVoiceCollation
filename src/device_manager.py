"""
⚠️ 废弃警告

此模块已迁移到 src.utils.device.device_manager

旧的用法（将在 v2.0.0 中移除）:
    from src.device_manager import detect_device, get_onnx_providers

新的用法:
    from src.utils.device.device_manager import detect_device, get_onnx_providers

迁移指南: docs/proposals/legacy-module-migration.md
"""
import warnings
from src.utils.device.device_manager import (
    is_torch_available,
    is_cuda_available,
    get_cuda_device_count,
    is_onnxruntime_available,
    get_onnxruntime_providers,
    detect_device,
    get_onnx_providers,
    print_device_info,
)

warnings.warn(
    "src.device_manager 已废弃，请使用 src.utils.device.device_manager",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "is_torch_available",
    "is_cuda_available",
    "get_cuda_device_count",
    "is_onnxruntime_available",
    "get_onnxruntime_providers",
    "detect_device",
    "get_onnx_providers",
    "print_device_info",
]
