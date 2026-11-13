package com.wime.app;

import android.util.Log;
import android.webkit.JavascriptInterface;

/** JS 桥接: 连接电脑地址 / 切换全屏, 动作串行化后切到 UI 线程执行 */
class JsBridge implements Runnable {

    private final MainActivity act;
    private String action = "";  // 待执行动作

    JsBridge(MainActivity act) {
        this.act = act;
    }

    /** 网页扫码成功后调用, 跳到电脑地址 */
    @JavascriptInterface
    public void connect(String url) {
        Log.i("WIME-NATIVE", "桥接收到的地址: " + url);
        action = "connect:" + url;
        act.runOnUiThread(this);
    }

    /** 网页点全屏按钮调用, 原生切沉浸模式(不动视图结构, 输入法不受影响) */
    @JavascriptInterface
    public void toggleFullscreen() {
        action = "fullscreen";
        act.runOnUiThread(this);
    }

    @Override
    public void run() {
        if (action.startsWith("connect:")) {
            act.loadRemote(action.substring(8));
        } else {
            act.toggleImmersive();
        }
    }
}
