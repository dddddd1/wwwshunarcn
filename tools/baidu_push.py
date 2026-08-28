#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度搜索资源平台 主动推送 + sitemap 提交 工具
============================================
作用：把站点 URL / sitemap 主动推送给百度，让蜘蛛尽快抓取，
      加快首页图片及文章页被百度收录。

使用前准备：
1. 登录 百度搜索资源平台 https://ziyuan.baidu.com/
2. 在「站点管理」添加并验证站点 www.shunar.cn
3. 在「普通收录 → 资源提交 → 主动推送」页面拿到 接口调用地址，
   里面包含 site 和 token 两个参数
4. 把下面 SITE / TOKEN 换成你自己的值

本地运行（你自己的终端，能联网）：
    python3 tools/baidu_push.py --all          # 推送全部URL + 提交两个sitemap
    python3 tools/baidu_push.py --push-urls    # 只推送 sitemap.xml 里的URL
    python3 tools/baidu_push.py --submit-sitemap  # 只提交 sitemap 文件
"""

import os
import sys
import urllib.request
import urllib.error

# ========== 在这里填你自己的 ==========
SITE = "www.shunar.cn"          # 站点域名（与搜索资源平台一致）
TOKEN = "____YOUR_BAIDU_TOKEN____"   # 接口调用 token
# =====================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUSH_API = f"http://data.zz.baidu.com/urls?site={SITE}&token={TOKEN}"
SITEMAP_API = f"http://data.zz.baidu.com/sitemap?site={SITE}&token={TOKEN}"

UA = {"Content-Type": "text/plain", "User-Agent": "shunar-baidu-push/1.0"}


def _post(api, payload):
    data = payload.encode("utf-8")
    req = urllib.request.Request(api, data=data, headers=UA, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return f"HTTP错误 {e.code}: {e.read().decode('utf-8','ignore')}"
    except Exception as e:  # noqa
        return f"请求失败: {e}"


def read_urls_from_sitemap(path):
    """从 sitemap.xml 提取所有 <loc> 里的 URL"""
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read()
    except FileNotFoundError:
        return []
    import re
    return re.findall(r"<loc>([^<]+)</loc>", txt)


def push_urls():
    """主动推送 URL（普通收录）"""
    sitemap = os.path.join(BASE_DIR, "sitemap.xml")
    urls = read_urls_from_sitemap(sitemap)
    if not urls:
        return "未找到 sitemap.xml 或其中无 URL"
    body = "\n".join(urls)
    print(f"[推送] 共 {len(urls)} 个URL -> {PUSH_API.split('?')[0]}")
    resp = _post(PUSH_API, body)
    print("[百度返回]", resp)
    return resp


def submit_sitemap():
    """提交 sitemap 文件（含图片 sitemap，便于图片收录）"""
    files = ["sitemap.xml", "sitemap-images.xml"]
    out = []
    for name in files:
        p = os.path.join(BASE_DIR, name)
        if not os.path.exists(p):
            print(f"[跳过] {name} 不存在")
            continue
        url = f"https://www.shunar.cn/{name}"
        print(f"[提交] {url}")
        resp = _post(SITEMAP_API, url)
        print(f"[百度返回] {resp}")
        out.append(resp)
    return "\n".join(out)


def main():
    if TOKEN.startswith("____"):
        print("⚠️ 请先在脚本顶部把 SITE / TOKEN 改成你百度站长平台的真实值")
        sys.exit(1)

    do_all = "--all" in sys.argv
    do_urls = "--push-urls" in sys.argv or do_all
    do_sm = "--submit-sitemap" in sys.argv or do_all

    if do_urls:
        push_urls()
    if do_sm:
        submit_sitemap()

    if not (do_urls or do_sm):
        print("用法：")
        print("  python3 tools/baidu_push.py --all              # 推荐")
        print("  python3 tools/baidu_push.py --push-urls        # 只推URL")
        print("  python3 tools/baidu_push.py --submit-sitemap   # 只提交sitemap")


if __name__ == "__main__":
    main()
