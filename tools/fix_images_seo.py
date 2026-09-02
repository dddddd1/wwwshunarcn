#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修复图片百度收录相关问题：
1. 修正 JSON-LD ImageObject 中重复的路径 bug
2. 将所有 img src 改为绝对域名 URL
3. 按图片真实内容为 alt/title 差异化命名
4. 重新生成 sitemap-images.xml，包含唯一图片、唯一 title、caption
"""
import os
import re
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "https://www.shunar.cn"

# 图片文件 -> 准确的中文名（描述图片真实内容）
IMG_NAMES = {
    "diamond-sorting-machine.jpg": "金刚石选型机",
    "diamond-shape-sorting-machine.jpg": "金刚石形状分选机",
    "micro-beads-001-10mm.jpg": "金刚石微粉10mm颗粒",
    "zirconia-bead-separator.jpg": "氧化锆球分离机",
    "zirconia-bead-separator-2.jpg": "氧化锆球分离设备",
    "zirconia-bead-screening-machine.jpg": "氧化锆球筛选机",
    "zirconia-bead-sorting-machine.jpg": "氧化锆球分选机",
    "ceramic-ball-screening-machine.jpg": "陶瓷球筛选机",
    "ceramic-ball-sifting-machine.jpg": "陶瓷球筛分机",
    "ceramic-bead-screening-machine.jpg": "陶瓷微珠筛选机",
    "ceramic-bead-sorting-machine-delivery.jpg": "陶瓷微珠分选机发货",
}

# 英文图片名 -> 描述性 (用于 caption)
IMG_CAPTIONS = {
    "diamond-sorting-machine.jpg": "工厂实拍金刚石选型机设备",
    "diamond-shape-sorting-machine.jpg": "金刚石形状分选机结构特写",
    "micro-beads-001-10mm.jpg": "金刚石微粉颗粒",
    "zirconia-bead-separator.jpg": "氧化锆球分离机现场图",
    "zirconia-bead-separator-2.jpg": "氧化锆球分离设备细节",
    "zirconia-bead-screening-machine.jpg": "氧化锆球筛选机设备照片",
    "zirconia-bead-sorting-machine.jpg": "氧化锆球分选机工作实拍",
    "ceramic-ball-screening-machine.jpg": "陶瓷球筛选机",
    "ceramic-ball-sifting-machine.jpg": "陶瓷球筛分机",
    "ceramic-bead-screening-machine.jpg": "陶瓷微珠筛选机产品图",
    "ceramic-bead-sorting-machine-delivery.jpg": "陶瓷微珠分选机发货现场",
}


def get_img_name(filename):
    base = os.path.basename(filename)
    return IMG_NAMES.get(base, "金刚石选型机")


def get_img_caption(filename):
    base = os.path.basename(filename)
    return IMG_CAPTIONS.get(base, "金刚石选型机实拍")


def fix_jsonld(content):
    # 修正重复路径 bug: upload/2026-08/zb_users/upload/2026-08/xxx.jpg
    content = re.sub(
        r"(upload/2026-08/)zb_users/upload/2026-08/",
        r"\1",
        content,
    )
    # 将 JSON-LD 中的 name/description 按图片内容差异化
    def fix_imgobj(m):
        block = m.group(0)
        urlm = re.search(r'"contentUrl":\s*"([^"]+)"', block)
        if urlm:
            img = urlm.group(1)
            name = get_img_name(img)
            caption = get_img_caption(img)
            block = re.sub(r'"name":\s*"[^"]*"', '"name": "%s"' % name, block)
            block = re.sub(r'"description":\s*"[^"]*"', '"description": "%s"' % caption, block)
        return block
    return re.sub(r'\{[^{}]*"@type":\s*"ImageObject"[^{}]*\}', fix_imgobj, content)


def fix_img_src(content):
    def repl(m):
        attrs = m.group(1)
        # 找出 src
        srcm = re.search(r'src="([^"]*)"', attrs)
        if not srcm:
            return m.group(0)
        src = srcm.group(1)
        new_src = src
        if src.startswith("../"):
            new_src = DOMAIN + "/" + src[3:]
        elif src.startswith("zb_users/"):
            new_src = DOMAIN + "/" + src
        elif src.startswith("/zb_users/"):
            new_src = DOMAIN + src
        attrs = attrs.replace('src="%s"' % src, 'src="%s"' % new_src)
        # 按图片内容设置 alt/title
        if "zb_users/upload/2026-08/" in new_src:
            name = get_img_name(new_src)
            if 'alt="' in attrs:
                attrs = re.sub(r'alt="[^"]*"', 'alt="%s"' % name, attrs)
            else:
                attrs += ' alt="%s"' % name
            if 'title="' in attrs:
                attrs = re.sub(r'title="[^"]*"', 'title="%s"' % name, attrs)
        return "<img" + attrs + ">"

    return re.sub(r'<img\s([^>]*)>', repl, content)


def fix_mip_img_src(content):
    """修正正文中的 mip-img 标签为绝对路径"""
    def repl(m):
        attrs = m.group(1)
        srcm = re.search(r'src="([^"]*)"', attrs)
        if not srcm:
            return m.group(0)
        src = srcm.group(1)
        new_src = src
        if src.startswith("../"):
            new_src = DOMAIN + "/" + src[3:]
        attrs = attrs.replace('src="%s"' % src, 'src="%s"' % new_src)
        return "<mip-img" + attrs + ">"

    return re.sub(r'<mip-img\s([^>]*)>', repl, content)


def process_html(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    new = fix_img_src(content)
    new = fix_mip_img_src(new)
    new = fix_jsonld(new)
    if new != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return True
    return False


def collect_images_per_post():
    """收集每个 post 页面使用的图片清单"""
    mapping = {}
    for path in glob.glob(os.path.join(ROOT, "post", "*.html")):
        n = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        imgs = []
        for srcm in re.finditer(r'src="([^"]*zb_users/upload/2026-08/[^"]*)"', content):
            url = srcm.group(1)
            if url.startswith("../"):
                url = DOMAIN + "/" + url[3:]
            imgs.append(url)
        # 去重保持顺序
        seen = []
        for i in imgs:
            if i not in seen:
                seen.append(i)
        # 取该页面对应的文章编号排序
        mapping[n] = seen
    return mapping


def gen_sitemap_images(mapping):
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">')
    # 首页：收录全部 11 张上传图片，确保未被 post 引用的陶瓷图也被收录
    index_imgs = []
    for fname in IMG_NAMES:
        index_imgs.append(DOMAIN + "/zb_users/upload/2026-08/" + fname)
    lines.append("  <url>")
    lines.append("    <loc>%s/</loc>" % DOMAIN)
    for u in index_imgs:
        lines.append("    <image:image>")
        lines.append("      <image:loc>%s</image:loc>" % u)
        lines.append("      <image:title>%s</image:title>" % get_img_name(u))
        lines.append("      <image:caption>%s</image:caption>" % get_img_caption(u))
        lines.append("    </image:image>")
    lines.append("  </url>")
    # 各 post
    for n in sorted(mapping.keys(), key=lambda x: int(re.sub(r"\D", "", x) or 0)):
        postnum = re.sub(r"\D", "", n)
        if not postnum:
            continue
        loc = "%s/post/%s.html" % (DOMAIN, postnum)
        imgs = mapping[n]
        if not imgs:
            continue
        lines.append("  <url>")
        lines.append("    <loc>%s</loc>" % loc)
        for u in imgs:
            lines.append("    <image:image>")
            lines.append("      <image:loc>%s</image:loc>" % u)
            lines.append("      <image:title>%s</image:title>" % get_img_name(u))
            lines.append("      <image:caption>%s</image:caption>" % get_img_caption(u))
            lines.append("    </image:image>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    changed = 0
    for path in glob.glob(os.path.join(ROOT, "*.html")):
        if process_html(path):
            changed += 1
            print("更新:", os.path.basename(path))
    for path in glob.glob(os.path.join(ROOT, "post", "*.html")):
        if process_html(path):
            changed += 1
            print("更新:", os.path.join("post", os.path.basename(path)))
    print("共更新 HTML 文件:", changed)

    mapping = collect_images_per_post()
    sitemap = gen_sitemap_images(mapping)
    with open(os.path.join(ROOT, "sitemap-images.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap)
    print("已生成 sitemap-images.xml，包含", sum(len(v) for v in mapping.values()), "条图片记录")
    # 显示首页图集
    indexall = set()
    for v in mapping.values():
        indexall.update(v)
    print("唯一图片数:", len(indexall))


if __name__ == "__main__":
    main()