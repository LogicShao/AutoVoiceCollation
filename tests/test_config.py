"""
配置管理模块单元测试

注意：本测试文件已过时，测试的是旧的配置系统。
新的配置系统基于 Pydantic，不再需要测试这些内部函数。

如需测试新配置系统，请参考：
- src/utils/config/ 目录下的配置模块
- Pydantic 自动处理类型转换和验证
"""

import pytest

# 标记整个模块为已废弃
pytestmark = pytest.mark.skip(reason="旧配置系统测试已废弃，新系统基于 Pydantic")


def test_placeholder():
    """占位测试，防止 pytest 报错"""
    pass
