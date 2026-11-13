# -*- coding: utf-8 -*-
"""
手机当电脑鼠标键盘 - 服务端
运行后手机浏览器访问提示的地址即可(手机和电脑需在同一局域网)
依赖: pip install pyautogui pyperclip
"""
import configparser
import json
import os
import socket
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image  # 二维码缩放用

import pyautogui
import pyperclip
import qrcode
from PIL import ImageTk
import tkinter as tk

# index.html 与本文件在同一目录, 这样无论从哪里启动都能找到
INDEX_PATH = os.path.join(os.path.dirname(__file__), "index.html")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.ini")  # 配置文件名

DISCOVER_PORT = 9999        # 手机自动发现电脑用的 UDP 端口
DISCOVER_MAGIC = b"WIME_DISCOVER"  # 手机广播的探测内容

pyautogui.FAILSAFE = False  # 关闭"鼠标甩到屏幕角落就中止程序"的安全机制, 避免误触发
pyautogui.PAUSE = 0         # 取消每次调用后的默认延时, 让鼠标移动更流畅

OP_LOCK = threading.Lock()  # 文字/按键串行锁: 剪贴板复制粘贴必须一次完成, 否则丢字乱序


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
                with OP_LOCK:           # 复制+粘贴必须原子完成, 避免与其他按键交错
                    pyperclip.copy(text)
                    time.sleep(0.01)    # 等剪贴板真正写入
                    pyautogui.hotkey("ctrl", "v")
        elif t == "key":     # 特殊按键: enter / esc / up 等, count 为连按次数
            with OP_LOCK:
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
    img = qrcode.make(url).resize((420, 420), Image.NEAREST)  # 大尺寸加锐利, 方便手机识别
    root = tk.Tk()
    root.title("扫码连接")
    root.attributes("-topmost", True)  # 窗口置顶, 不被其他窗口挡住
    root.resizable(False, False)
    photo = ImageTk.PhotoImage(img)  # 保存引用, 防止图片被垃圾回收
    tk.Label(root, text="手机扫码连接", font=("微软雅黑", 14), bg="white").pack(
        pady=(14, 6), fill="x")
    tk.Label(root, image=photo, bg="white").pack(padx=24, pady=6)
    tk.Label(root, text=url, font=("Consolas", 12), bg="white").pack(pady=(0, 14))
    root.mainloop()


def load_config():
    """读取 config.ini, 文件不存在时自动生成一份默认配置"""
    cfg = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH, encoding="utf-8")
    if not cfg.has_section("server"):
        cfg["server"] = {"port": "8888", "show_qr": "true"}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            cfg.write(f)
    return cfg


def udp_discover(port):
    """UDP 发现服务: 收到手机广播就回复本机地址, 手机据此自动连接"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", DISCOVER_PORT))
    except OSError:
        print(f"UDP {DISCOVER_PORT} 端口被占用, 自动发现不可用(手动输入 IP 仍可连接)")
        return
    while True:
        try:
            data, addr = s.recvfrom(1024)
        except OSError:
            break
        if data == DISCOVER_MAGIC:
            # 回复 IP/端口/主机名, 多台电脑时手机靠主机名区分
            info = json.dumps({"ip": get_local_ip(), "port": port,
                               "name": socket.gethostname()}, ensure_ascii=False)
            s.sendto(info.encode("utf-8"), addr)


def make_tray_icon():
    """托盘图标: 优先用同目录的 tray.png, 没有就用代码画的简版"""
    path = os.path.join(os.path.dirname(__file__), "tray.png")
    if os.path.exists(path):
        return Image.open(path).convert("RGBA")
    from PIL import ImageDraw, ImageFont
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 62, 62], radius=12, fill=(90, 90, 124))
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    d.text((20, 8), "W", fill="white", font=font)
    return img


def run_tray(url):
    """后台运行: 常驻托盘图标, 右键可打开页面/查看二维码/退出"""
    import webbrowser
    import pystray
    from pystray import MenuItem as Item

    def open_page(icon, item):
        webbrowser.open(url)

    def show_qr_image(icon, item):
        # 二维码存成临时图片, 用系统看图工具打开, 不依赖 tkinter
        path = os.path.join(tempfile.gettempdir(), "wime_qr.png")
        qrcode.make(url).resize((420, 420), Image.NEAREST).save(path)
        os.startfile(path)

    def quit_app(icon, item):
        icon.stop()

    menu = pystray.Menu(
        Item("打开控制页", open_page, default=True),   # 双击图标默认打开页面
        Item("显示二维码", show_qr_image),
        Item("退出", quit_app),
    )
    icon = pystray.Icon("WIME", make_tray_icon(),
                        f"WIME 服务运行中\n{url}", menu)

    def setup(i):
        i.visible = True
        # 启动气泡提示, 让用户知道程序在托盘里运行(Windows 默认把新图标收进隐藏区)
        try:
            i.notify(f"服务已启动\n{url}", "WIME")
        except Exception:
            pass

    icon.run(setup=setup)   # 阻塞在这里, 托盘常驻


def start():
    """启动服务: HTTP 服务 + UDP 自动发现, 二维码窗口是否弹出由 config.ini 控制"""
    cfg = load_config()
    port = cfg["server"].getint("port", fallback=8888)
    show_qr_flag = cfg["server"].getboolean("show_qr", fallback=True)
    url = f"http://{get_local_ip()}:{port}"
    print(f"手机自动发现或手动输入: {url}")
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=udp_discover, args=(port,), daemon=True).start()
    if show_qr_flag:
        show_qr(url)          # 阻塞在扫码窗口, 关闭窗口时程序退出
    else:
        print("已在 config.ini 中关闭二维码弹窗, 程序缩到系统托盘运行")
        try:
            run_tray(url)     # 阻塞在托盘, 右键菜单退出
        except Exception as e:
            print(f"托盘启动失败({e}), 改为静默运行, 按 Ctrl+C 退出")
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    start()
