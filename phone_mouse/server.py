# -*- coding: utf-8 -*-
"""
手机当电脑鼠标键盘 - 服务端
运行后手机浏览器访问提示的地址即可(手机和电脑需在同一局域网)
依赖: pip install pyautogui pyperclip
"""
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pyautogui
import pyperclip
import qrcode
from PIL import ImageTk
import tkinter as tk

# index.html 与本文件在同一目录, 这样无论从哪里启动都能找到
INDEX_PATH = os.path.join(os.path.dirname(__file__), "index.html")

pyautogui.FAILSAFE = False  # 关闭"鼠标甩到屏幕角落就中止程序"的安全机制, 避免误触发
pyautogui.PAUSE = 0         # 取消每次调用后的默认延时, 让鼠标移动更流畅


class Handler(BaseHTTPRequestHandler):
    """处理网页请求: GET 返回控制页面, POST 接收控制指令"""

    def _send(self, code, body=b"", ctype="text/html; charset=utf-8"):
        """统一发送响应"""
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """返回手机端控制页面"""
        if self.path == "/":
            with open(INDEX_PATH, "rb") as f:
                self._send(200, f.read())
        else:
            self._send(404, b"not found")

    def do_POST(self):
        """接收 JSON 指令并转化为鼠标键盘操作"""
        if self.path != "/api":
            return self._send(404)
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        t = data.get("type")
        if t == "move":      # 相对移动鼠标
            pyautogui.moveRel(data.get("dx", 0), data.get("dy", 0))
        elif t == "click":   # 点击, button 为 left / right
            pyautogui.click(button=data.get("button", "left"))
        elif t == "scroll":  # 滚动滚轮, 正数向上
            pyautogui.scroll(data.get("dy", 0))
        elif t == "text":    # 输入文字(通过剪贴板粘贴, 支持中文)
            text = data.get("text", "")
            if text:
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
        elif t == "key":     # 特殊按键: enter / esc / up 等, count 为连按次数
            pyautogui.press(data.get("key"), presses=data.get("count", 1))
        self._send(200, b"ok", "text/plain")

    def log_message(self, *args):
        """屏蔽每个请求的日志, 避免刷屏"""
        pass


def get_local_ip():
    """获取本机局域网 IP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # 不会真的发包, 只为确定出口网卡
        return s.getsockname()[0]
    finally:
        s.close()


def show_qr(url):
    """弹出二维码窗口, 手机扫码即可连接, 关闭窗口则程序退出"""
    img = qrcode.make(url).resize((300, 300))  # 生成二维码图片
    root = tk.Tk()
    root.title("扫码连接")
    root.resizable(False, False)
    photo = ImageTk.PhotoImage(img)  # 保存引用, 防止图片被垃圾回收
    tk.Label(root, text="手机扫码连接", font=("微软雅黑", 14)).pack(pady=(14, 6))
    tk.Label(root, image=photo).pack(padx=24, pady=6)
    tk.Label(root, text=url, font=("Consolas", 12)).pack(pady=(0, 14))
    root.mainloop()


def start(port=8888):
    """启动服务: 后台线程跑 HTTP 服务, 主线程显示扫码窗口"""
    url = f"http://{get_local_ip()}:{port}"
    print(f"手机扫码连接, 或浏览器打开: {url}")
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    show_qr(url)  # 阻塞在扫码窗口, 关闭窗口时程序退出


if __name__ == "__main__":
    start()
