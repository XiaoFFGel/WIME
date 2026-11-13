package com.wime.app;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;

/**
 * WIME 主界面: 一个 WebView, 先打开内置的连接页,
 * 连接后加载电脑上的遥控页面(触屏板/直播输入都在网页里)
 */
public class MainActivity extends Activity {

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // 扫码需要摄像头: 启动时就申请运行时权限
        if (Build.VERSION.SDK_INT >= 23 &&
                checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, 1);
        }
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);              // 遥控页面需要 JS
        // 网页申请摄像头时直接授予(用于扫码)
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                request.grant(request.getResources());
            }
        });
        web.loadUrl("file:///android_asset/launcher.html");  // 内置连接页
        setContentView(web);
    }

    @Override
    public void onBackPressed() {
        // 返回键: WebView 能后退就后退, 否则正常退出
        if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
