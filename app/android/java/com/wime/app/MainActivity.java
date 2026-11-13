package com.wime.app;

import android.app.Activity;
import android.os.Bundle;
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
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);              // 遥控页面需要 JS
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
