"""控制台编码兼容。

Windows 上 Python 默认按控制台代码页（简体中文为 ``gbk``/``cp936``）编码标准输出，
而 Git Bash、VS Code 终端、CI 日志普遍按 UTF-8 解码，于是中文全部乱码：

.. code-block:: text

    $ tingwu check
    ��¼̬��Ч  userId=<你的 userId>        # 实际是「登录态有效」

本模块提供 :func:`enable_utf8_output`，把 Python 侧的流编码切到 UTF-8，
**不改控制台代码页**，因此不影响管道与文件重定向，也不产生全局副作用。
"""

from __future__ import annotations

import os
import sys


def enable_utf8_output(*, force: bool = False) -> bool:
    """把 ``sys.stdout`` / ``sys.stderr`` 切到 UTF-8。

    Args:
        force: 为 True 时即使已设置 ``PYTHONIOENCODING`` 也强制切换。

    Returns:
        是否至少成功重配置了一个流。

    Note:
        默认尊重 ``PYTHONIOENCODING``——用户显式指定编码时不越权覆盖。
        流被重定向到不支持 ``reconfigure`` 的对象（如旧式包装器）时静默跳过。
        任何失败都不会抛异常：输出编码不该让程序崩掉。
    """
    if not force and os.environ.get("PYTHONIOENCODING"):
        return False

    changed = False
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        # 已经是 UTF-8 就不动，避免无谓的重建
        if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
            changed = True
            continue
        try:
            reconfigure(encoding="utf-8")
            changed = True
        except (ValueError, OSError, AttributeError):
            pass
    return changed
