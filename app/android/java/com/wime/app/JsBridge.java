package com.wime.app;

import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

/** 暴露给网页 JS 的桥接: 由原生代码完成跳转(WebView 会拦截 file 页的 http 跳转) */
class JsBridge implements Runnable {

    private final WebView web;
    private String url;  // 待加载的电脑地址

    JsBridge(WebView web) {
        this.web = web;
    }

    /** 网页扫码成功后调用, 跳到电脑地址 */
    @JavascriptInterface
    public void connect(String u) {
        Log.i("WIME-NATIVE", "桥接收到的地址: " + u);
        url = u;
        web.post(this);  // 切回 UI 线程再加载
    }

    @Override
    public void run() {
        Log.i("WIME-NATIVE", "开始加载: " + url);
        web.loadUrl(url);
    }
}
