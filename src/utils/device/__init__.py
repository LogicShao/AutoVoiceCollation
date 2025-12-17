# 向后兼容导入
from .device_manager import detect_device, get_onnx_providers, print_device_info

__all__ = ["detect_device", "get_onnx_providers", "print_device_info"]
