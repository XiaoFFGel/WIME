# -*- coding: utf-8 -*-
"""
程序入口: 运行 python main.py 启动"手机当电脑鼠标键盘"服务
打包成 exe 后同样从这个入口启动
"""
import os
import sys

# 打包成无控制台的 exe 时 stdout/stderr 为 None, 直接 print 会报错
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from phone_mouse.server import start


if __name__ == "__main__":
    try:
        start()
    except Exception:
        # 无控制台时错误弹窗提示, 方便定位启动失败的原因
        import traceback
        import tkinter.messagebox as mb

        mb.showerror("WIME 启动失败", traceback.format_exc())
