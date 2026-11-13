package com.wime.app;

import android.util.Log;
import android.webkit.JavascriptInterface;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.util.LinkedHashSet;
import java.util.Set;

/** 局域网自动发现电脑: 广播探测包, 收集所有回复后交给网页 */
class UdpDiscover implements Runnable {

    private static final int PORT = 9999;                 // 与电脑端 server.py 一致
    private static final String MAGIC = "WIME_DISCOVER";
    private final MainActivity act;

    UdpDiscover(MainActivity act) {
        this.act = act;
    }

    /** 网页调用: 开始搜索(网络操作必须放子线程) */
    @JavascriptInterface
    public void find() {
        new Thread(this).start();
    }

    @Override
    public void run() {
        Set<String> found = new LinkedHashSet<>();  // 去重, 每台电脑只保留一条
        DatagramSocket sock = null;
        try {
            sock = new DatagramSocket();
            sock.setBroadcast(true);
            sock.setSoTimeout(300);                 // 每次接收最多等 300ms
            byte[] msg = MAGIC.getBytes("UTF-8");
            // 先发全网广播
            sock.send(new DatagramPacket(msg, msg.length,
                    InetAddress.getByName("255.255.255.255"), PORT));
            // 部分路由器不转发 255.255.255.255, 再发一次本网段广播
            String ip = act.lanIp();
            if (ip != null && ip.contains(".")) {
                String bcast = ip.substring(0, ip.lastIndexOf('.')) + ".255";
                sock.send(new DatagramPacket(msg, msg.length,
                        InetAddress.getByName(bcast), PORT));
            }
            long end = System.currentTimeMillis() + 1800;   // 总共收集 1.8 秒
            while (System.currentTimeMillis() < end) {
                byte[] buf = new byte[512];
                DatagramPacket p = new DatagramPacket(buf, buf.length);
                try {
                    sock.receive(p);
                    String s = new String(p.getData(), 0, p.getLength(), "UTF-8");
                    found.add(s);
                    Log.i("WIME-NATIVE", "发现电脑: " + s);
                } catch (Exception e) {
                    // 超时继续等下一台
                }
            }
        } catch (Exception e) {
            Log.e("WIME-NATIVE", "自动发现失败: " + e);
        } finally {
            if (sock != null) sock.close();
        }
        JSONArray arr = new JSONArray();
        for (String s : found) {
            try {
                arr.put(new JSONObject(s));
            } catch (Exception ignored) {
            }
        }
        act.onDiscoverResult(arr.toString());       // 结果交回网页展示
    }
}
