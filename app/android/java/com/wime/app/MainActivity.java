package com.wime.app;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.webkit.WebSettings;
import android.webkit.WebView;

/**
 * WIME 主界面: 一个 WebView, 先打开内置的连接页,
 * 连接后加载电脑上的遥控页面(触屏板/直播输入都在网页里)
 */
public class MainActivity extends Activity {

    private WebView web;
    private WebChromeClientImpl chrome;  // 网页交互支持(全屏状态由它管理)

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
        web.addJavascriptInterface(new JsBridge(web), "Wime");  // JS 跳桥接
        // 焦点设置: 保证点击输入框时输入法能正常弹出
        web.setFocusable(true);
        web.setFocusableInTouchMode(true);
        web.requestFocus();
        chrome = new WebChromeClientImpl(this, web);  // 摄像头授权/弹窗/全屏
        web.setWebChromeClient(chrome);
        web.loadUrl("file:///android_asset/launcher.html");  // 内置连接页
        Log.i("WIME-NATIVE", "onCreate, 页面加载完成");
        setContentView(web);
    }

    @Override
    public void onBackPressed() {
        // 返回键: 先退出网页全屏, 再后退, 最后退出
        if (chrome.isFullscreen()) {
            chrome.onHideCustomView();
        } else if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
