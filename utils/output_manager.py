import logging
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from io import StringIO


@contextmanager
def suppress_output():
    """临时重定向stdout和stderr，抑制依赖库输出。"""
    with StringIO() as buf_out, StringIO() as buf_err:
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            yield


def set_logging_level(level=logging.WARNING):
    """设置全局日志级别，减少依赖库日志输出。"""
    logging.basicConfig(level=level)
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).setLevel(level)
