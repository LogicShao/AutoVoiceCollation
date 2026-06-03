"""API schema compatibility package.

当前请求/响应模型仍集中定义在 api.py。保留本包是为了避免外部代码
导入 src.api.schemas 时失败；仓库内未发现对该包的直接引用。
"""
