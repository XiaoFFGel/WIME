package com.wime.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.ConsoleMessage;
import android.webkit.JsResult;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.widget.FrameLayout;

/** WebView 的网页交互支持: 摄像头授权、JS 弹窗、控制台日志、网页全屏 */
class WebChromeClientImpl extends WebChromeClient {

    private final Activity act;
    private final WebView web;          // 主 WebView, 退出全屏后焦点还给它
    private View customView;            // 全屏时的自定义视图
    private CustomViewCallback cb;      // 退出全屏的回调

    WebChromeClientImpl(Activity act, WebView web) {
        this.act = act;
        this.web = web;
    }

    @Override
    public void onPermissionRequest(PermissionRequest request) {
        Log.i("WIME-NATIVE", "网页请求权限: " + request.getResources());
        request.grant(request.getResources());
    }

    @Override
    public boolean onJsAlert(WebView view, String url, String message, JsResult result) {
        // WebView 默认不显示 JS alert, 这里手动弹窗
        new AlertDialog.Builder(view.getContext())
                .setTitle("提示")
                .setMessage(message)
                .setPositiveButton("确定", null)
                .create()
                .show();
        result.confirm();
        return true;
    }

    @Override
    public boolean onConsoleMessage(ConsoleMessage m) {
        Log.d("WIME", m.message());  // 网页控制台日志输出到 logcat
        return true;
    }

    /** 网页请求全屏(点全屏按钮): 把网页视图铺满窗口并隐藏系统栏 */
    @Override
    public void onShowCustomView(View view, CustomViewCallback callback) {
        if (customView != null) { callback.onCustomViewHidden(); return; }
        customView = view;
        cb = callback;
        act.getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        act.addContentView(view,
                new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                                             ViewGroup.LayoutParams.MATCH_PARENT));
    }

    /** 退出全屏: 移除自定义视图, 恢复系统栏, 焦点还给 WebView(否则输入法弹不出) */
    @Override
    public void onHideCustomView() {
        if (customView == null) return;
        act.getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE);
        ViewGroup parent = (ViewGroup) customView.getParent();
        if (parent != null) parent.removeView(customView);
        customView = null;
        if (cb != null) { cb.onCustomViewHidden(); cb = null; }
        web.requestFocus();
    }

    /** 是否正处于网页全屏状态 */
    boolean isFullscreen() {
        return customView != null;
    }
}
