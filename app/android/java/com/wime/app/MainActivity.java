package com.wime.app;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.webkit.WebSettings;
import android.webkit.WebView;

/**
 * WIME 主界面: 一个 WebView, 先打开内置的连接页,
 * 连接后加载电脑上的遥控页面(触屏板/直播输入都在网页里)
 */
public class MainActivity extends Activity {

    private WebView web;
    private boolean fullscreen = false;  // 当前是否处于全屏(沉浸)状态

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            init(savedInstanceState);
        } catch (Throwable e) {
            // 出错时弹窗显示原因, 方便定位闪退
            new AlertDialog.Builder(this)
                    .setTitle("WIME 出错")
                    .setMessage(Log.getStackTraceString(e))
                    .setPositiveButton("确定", null)
                    .show();
        }
    }

    private void init(Bundle savedInstanceState) {
        // 扫码需要摄像头: 启动时就申请运行时权限
        if (Build.VERSION.SDK_INT >= 23 &&
                checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, 1);
        }
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);              // 遥控页面需要 JS
        s.setDomStorageEnabled(true);              // 必须开启, 否则 localStorage 为 null
        s.setMediaPlaybackRequiresUserGesture(false);  // 扫码视频流需要自动播放
        web.addJavascriptInterface(new JsBridge(this), "Wime");  // JS 桥接
        web.addJavascriptInterface(new UdpDiscover(this), "WimeDiscover");  // 自动发现
        // 焦点设置: 保证点击输入框时输入法能正常弹出
        web.setFocusable(true);
        web.setFocusableInTouchMode(true);
        web.requestFocus();
        web.setWebChromeClient(new WebChromeClientImpl());  // 摄像头授权/JS弹窗/日志
        web.loadUrl("file:///android_asset/launcher.html");  // 内置连接页
        setContentView(web);
    }

    /** 扫码成功后由桥接调用, 加载电脑上的遥控页 */
    public void loadRemote(String url) {
        web.loadUrl(url);
    }

    /** 本机局域网 IP, 用于计算广播地址 */
    public String lanIp() {
        try {
            java.util.Enumeration<java.net.NetworkInterface> nis =
                    java.net.NetworkInterface.getNetworkInterfaces();
            while (nis.hasMoreElements()) {
                java.net.NetworkInterface ni = nis.nextElement();
                if (!ni.isUp() || ni.isLoopback()) continue;
                java.util.Enumeration<java.net.InetAddress> addrs = ni.getInetAddresses();
                while (addrs.hasMoreElements()) {
                    java.net.InetAddress a = addrs.nextElement();
                    if (a instanceof java.net.Inet4Address && !a.isLoopbackAddress()) {
                        return a.getHostAddress();
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    /** 发现结果回传给网页(切回 UI 线程, WebView 方法必须在主线程调用) */
    public void onDiscoverResult(final String json) {
        // 用 lambda 而非匿名内部类: d8 转换匿名类 $1.class 会崩溃
        runOnUiThread(() -> web.evaluateJavascript("onDiscover(" + jsString(json) + ")", null));
    }

    /** 把字符串安全转成 JS 字符串字面量, 避免引号换行破坏脚本 */
    private String jsString(String s) {
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'")
                .replace("\n", "\\n").replace("\r", "") + "'";
    }

    /** 全屏切换: 只切系统栏的显示隐藏, 不增删视图, 输入法始终正常 */
    public void toggleImmersive() {
        fullscreen = !fullscreen;
        View d = getWindow().getDecorView();
        if (fullscreen) {
            d.setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        } else {
            d.setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE);
        }
    }

    @Override
    public void onBackPressed() {
        // 返回键: 全屏时先退全屏, 再后退, 最后退出
        if (fullscreen) {
            toggleImmersive();
        } else if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
