#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import time
import socket
import requests
from collections import defaultdict
from urllib.parse import urlparse

# =========================
# 基础配置
# =========================
INPUT_FILE = "input.m3u"
OUTPUT_FILE = "output.m3u"
TIMEOUT = 6

# =========================
# 购物 / 广告台 精准过滤
# =========================
SHOPPING_CHANNELS = {
    "hsn", "qvc", "shophq", "jewelry",
    "购物", "家有购物", "优购物", "快乐购",
    "东森购物", "momo", "viva", "森森",
    "shop channel", "homeshopping",
}

AD_CHANNEL_KEYWORDS = {
    "广告", "ad ", "promo", "shopping",
    "brand", "marketing", "campaign",
}

# =========================
# 影视 / 剧集 白名单（防误杀）
# =========================
DRAMA_MOVIE_WHITELIST = {
    "cctv-6", "cctv-8", "电影", "影院", "影视",
    "凤凰中文", "凤凰资讯", "凤凰香港",
    "now", "tvb", "翡翠", "明珠",
}

# =========================
# EPG 精准映射
# =========================
EPG_ID_MAP = {
    "凤凰中文": "PhoenixChinese",
    "凤凰资讯": "PhoenixInfo",
    "凤凰香港": "PhoenixHK",
    "NOW星影": "NowBaoguMovies",
    "Now爆谷": "NowBaoguMovies",
    "中天新闻": "CTiNews",
    "亚洲卫视": "AsiaTV",
}

# =========================
# 工具函数
# =========================
def is_ad_or_shop(name: str) -> bool:
    n = name.lower()
    for w in DRAMA_MOVIE_WHITELIST:
        if w.lower() in n:
            return False
    for k in SHOPPING_CHANNELS | AD_CHANNEL_KEYWORDS:
        if k in n:
            return True
    return False


def is_stream_alive(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return False
        socket.setdefaulttimeout(TIMEOUT)
        socket.gethostbyname(host)
        return True
    except Exception:
        return False


def detect_quality(url: str) -> str:
    u = url.lower()
    if "2160" in u or "4k" in u:
        return "4K"
    if "1080" in u:
        return "1080P"
    if "720" in u:
        return "720P"
    return "HD"


# =========================
# 读取 M3U
# =========================
with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
    lines = [l.strip() for l in f if l.strip()]

channels = []
i = 0
while i < len(lines):
    if lines[i].startswith("#EXTINF"):
        extinf = lines[i]
        url = lines[i + 1] if i + 1 < len(lines) else ""
        channels.append((extinf, url))
        i += 2
    else:
        i += 1

# =========================
# 聚合频道
# =========================
all_channels = defaultdict(list)

for extinf, url in channels:
    name_match = re.search(r",(.+)$", extinf)
    if not name_match:
        continue

    name = name_match.group(1).strip()

    if is_ad_or_shop(name):
        continue

    if not is_stream_alive(url):
        continue

    all_channels[name].append((extinf, url))

# =========================
# 生成 final
# =========================
final = []

for name, items in all_channels.items():
    tvg_id = EPG_ID_MAP.get(name, "")
    logo = ""
    if tvg_id:
        logo = f'https://raw.githubusercontent.com/fanmingming/live/main/tv/{tvg_id}.png'

    for _, url in items:
        quality = detect_quality(url)

        extinf = f'#EXTINF:-1 tvg-name="{name}"'
        if tvg_id:
            extinf += f' tvg-id="{tvg_id}"'
        if logo:
            extinf += f' tvg-logo="{logo}"'
        extinf += f',{name} | {quality}'

        final.append((extinf, url))

# =========================
# 排序 + 编号（稳定）
# =========================
final.sort(key=lambda x: x[0])

sorted_final = []
channel_index = 1

for extinf, url in final:
    if 'tvg-chno' not in extinf:
        extinf = extinf.replace(
            '#EXTINF:-1 ',
            f'#EXTINF:-1 tvg-chno="{channel_index}" '
        )
    sorted_final.append((extinf, url))
    channel_index += 1

final = sorted_final

# =========================
# 写出文件
# =========================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for extinf, url in final:
        f.write(extinf + "\n")
        f.write(url + "\n")

print(f"✅ 完成：{len(final)} 条频道输出 → {OUTPUT_FILE}")