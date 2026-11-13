# -*- coding: utf-8 -*-
"""
把电脑端打包成单文件 exe
用法: python build_exe.py      产物: dist/WIME.exe
首次运行需要: pip install pyinstaller
"""
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(ROOT, "phone_mouse")
ICO = os.path.join(ROOT, "build_exe", "wime.ico")
DIST = os.path.join(ROOT, "dist")


def make_ico():
    """用应用图标生成多尺寸 ico, 作为 exe 图标"""
    src = Image.open(os.path.join(ROOT, "app", "icon_square_round.png")).convert("RGBA")
    os.makedirs(os.path.dirname(ICO), exist_ok=True)
    src.save(ICO, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                         (64, 64), (128, 128), (256, 256)])
    return ICO


def main():
    ico = make_ico()
    # 只读资源打进包里; config.ini 不打包, 首次运行会在 exe 旁边自动生成
    add = lambda name: ["--add-data", f"{os.path.join(PKG, name)}{os.pathsep}phone_mouse"]
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "WIME",
        "--icon", ico,
        *add("index.html"),
        *add("tray.png"),
        "--hidden-import", "pystray._win32",     # 托盘后端动态导入, 需显式声明
        "--hidden-import", "plyer.platforms.win.notification",
        "--distpath", DIST,
        "--workpath", os.path.join(ROOT, "build_exe"),
        "--specpath", os.path.join(ROOT, "build_exe"),
        os.path.join(ROOT, "main.py"),
    ]
    subprocess.run(args, check=True)
    exe = os.path.join(DIST, "WIME.exe")
    print(f"\n打包完成: {exe} ({os.path.getsize(exe) // 1024 // 1024} MB)")


if __name__ == "__main__":
    main()
