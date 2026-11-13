package com.wime.app;

import android.app.AlertDialog;
import android.util.Log;
import android.webkit.ConsoleMessage;
import android.webkit.JsResult;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebView;

/** WebView 的网页交互支持: 摄像头授权、JS alert 弹窗、控制台日志 */
class WebChromeClientImpl extends WebChromeClient {

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
}
