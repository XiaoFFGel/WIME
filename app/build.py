# -*- coding: utf-8 -*-
"""
WIME APK 构建脚本 (纯 Python 编排, 不需要 gradle / WSL / Android Studio)
首次运行会自动下载 Android 构建工具(约 100MB), 之后构建走本地缓存
用法: python build.py    产物: WIME.apk
"""
import glob
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

APP = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(APP, "android")          # 安卓工程源码目录
BUILD = os.path.join(APP, "build")          # 中间产物目录
TOOLS = os.path.join(APP, "tools")          # 构建工具目录
OUT = os.path.join(APP, "WIME.apk")         # 最终安装包

# Android 官方构建工具下载地址 (Google 仓库直链, 依次尝试直到成功)
BT_URL = "https://dl.google.com/android/repository/build-tools_r34-windows.zip"
PLAT_URLS = [
    "https://dl.google.com/android/repository/platform-34-ext7_r02.zip",
    "https://dl.google.com/android/repository/platform-34_r02.zip",
    "https://dl.google.com/android/repository/platform-34_r01.zip",
    "https://dl.google.com/android/repository/platform-33_r02.zip",
]


def download(url, dest):
    """下载文件并显示进度"""
    print(f"下载: {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"完成: {dest} ({os.path.getsize(dest) // 1024 // 1024} MB)")


def download_any(urls, dest):
    """依次尝试多个下载地址"""
    last_err = None
    for url in urls:
        try:
            download(url, dest)
            return
        except Exception as e:
            print(f"地址失效, 换下一个: {e}")
            last_err = e
    sys.exit(f"全部下载地址失败: {last_err}")


def ensure_tools():
    """确保 build-tools 和 android.jar 已就位, 没有就下载解压"""
    os.makedirs(TOOLS, exist_ok=True)
    # build-tools (含 aapt2 / d8 / zipalign / apksigner)
    bt_dir = os.path.join(TOOLS, "build-tools")
    if not os.path.exists(bt_dir):
        z = os.path.join(TOOLS, "bt.zip")
        download(BT_URL, z)
        with zipfile.ZipFile(z) as f:
            f.extractall(TOOLS)                 # 解压出的目录名不定, 统一改名
        inner = glob.glob(os.path.join(TOOLS, "android-*"))[0]
        os.rename(inner, bt_dir)
        os.remove(z)
    # platform (只要里面的 android.jar)
    jar = os.path.join(TOOLS, "platform", "android.jar")
    if not os.path.exists(jar):
        z = os.path.join(TOOLS, "plat.zip")
        if not os.path.exists(z):               # 上次已下载过就复用
            download_any(PLAT_URLS, z)
        with zipfile.ZipFile(z) as f:
            names = f.namelist()                # 找出压缩包里的 android.jar
            jar_in_zip = [n for n in names if n.endswith("/android.jar")][0]
            f.extract(jar_in_zip, TOOLS)
        os.makedirs(os.path.dirname(jar), exist_ok=True)
        shutil.move(os.path.join(TOOLS, jar_in_zip), jar)
        os.remove(z)
    return bt_dir, jar


def run(cmd, desc):
    """执行外部命令, 失败即退出"""
    print(f"== {desc}")
    r = subprocess.run(cmd, cwd=APP)
    if r.returncode != 0:
        sys.exit(f"{desc} 失败")


def find_keytool():
    """找 keytool: 先查 PATH, 再查 java.exe 同目录, 最后扫常见 JDK 安装目录"""
    kt = shutil.which("keytool")
    if kt:
        return kt
    java = shutil.which("java")
    if java:
        kt = os.path.join(os.path.dirname(java), "keytool.exe")
        if os.path.exists(kt):
            return kt
    # Oracle 垫片目录没有 keytool, 扫描真实 JDK 目录的 bin 子目录
    for d in glob.glob(r"C:\Program Files\Java\jdk-*\bin") + glob.glob(r"C:\Program Files\Eclipse Adoptium\jdk-*\bin"):
        kt = os.path.join(d, "keytool.exe")
        if os.path.exists(kt):
            return kt
    sys.exit("找不到 keytool, 请确认 JDK/JRE 已正确安装")


def main():
    bt_dir, android_jar = ensure_tools()
    aapt2 = os.path.join(bt_dir, "aapt2.exe")
    d8 = os.path.join(bt_dir, "d8.bat")
    zipalign = os.path.join(bt_dir, "zipalign.exe")
    apksigner = os.path.join(bt_dir, "apksigner.bat")
    keystore = os.path.join(BUILD, "wime.keystore")

    # 1. 编译资源并链接出基础 apk (清单 + assets)
    unsigned = os.path.join(BUILD, "unsigned.apk")
    run([aapt2, "link", "-o", unsigned, "-I", android_jar,
         "--manifest", os.path.join(SRC, "AndroidManifest.xml"),
         "-A", os.path.join(SRC, "assets")], "aapt2 链接资源")

    # 2. 编译 Java 代码 (源码目录下所有 .java)
    obj = os.path.join(BUILD, "obj")
    shutil.rmtree(obj, ignore_errors=True)
    os.makedirs(obj)
    sources = glob.glob(os.path.join(SRC, "java", "**", "*.java"), recursive=True)
    run(["javac", "--release", "8", "-encoding", "UTF-8",
         "-classpath", android_jar, "-d", obj] + sources, "javac 编译")

    # 3. 转成 dex (d8 逐个喂内部类 class 会报内部错误, 打成 zip 传给它)
    classes = glob.glob(os.path.join(obj, "**", "*.class"), recursive=True)
    jar = os.path.join(BUILD, "classes.zip")
    with zipfile.ZipFile(jar, "w") as f:
        for c in classes:
            f.write(c, os.path.relpath(c, obj))
    run([d8, "--release", "--lib", android_jar, "--output", BUILD, jar], "d8 转 dex")

    # 4. 把 classes.dex 塞进 apk
    with zipfile.ZipFile(unsigned, "a") as f:
        f.write(os.path.join(BUILD, "classes.dex"), "classes.dex")

    # 5. 对齐 (zipalign 必须在签名之前)
    aligned = os.path.join(BUILD, "aligned.apk")
    run([zipalign, "-f", "4", unsigned, aligned], "zipalign 对齐")

    # 6. 生成签名用的 keystore (已存在则复用)
    if not os.path.exists(keystore):
        run([find_keytool(), "-genkeypair", "-keystore", keystore, "-alias", "wime",
             "-storepass", "wime123", "-keypass", "wime123",
             "-keyalg", "RSA", "-validity", "10000", "-dname", "CN=WIME"],
            "生成 keystore")

    # 7. 签名, 得到最终安装包
    run([apksigner, "sign", "--ks", keystore, "--ks-pass", "pass:wime123",
         "--out", OUT, aligned], "apksigner 签名")

    print(f"\n构建完成: {OUT} ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    os.makedirs(BUILD, exist_ok=True)
    main()
