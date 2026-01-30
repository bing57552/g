#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
from collections import defaultdict

# =========================
# 基础配置
# =========================
M3U_SOURCE_URL = "https://gh-proxy.com/raw.githubusercontent.com/suxuang/myIPTV/main/ipv4.m3u"  # 港澳台+大陸源較齊
INPUT_FILE = "input.m3u"
OUTPUT_FILE = "output_best.m3u"
TIMEOUT = 5

# =========================
# 购物 / 广告台 过滤
# =========================
SHOPPING_CHANNELS = {"hsn", "qvc", "shophq", "jewelry", "购物", "家有购物", "优购物", "快乐购", "东森购物", "momo", "viva", "森森", "shop channel", "homeshopping"}
AD_CHANNEL_KEYWORDS = {"广告", "ad ", "promo", "shopping", "brand", "marketing", "campaign"}

# =========================
# 白名单（防誤殺） - 擴大 OTT 頻道
# =========================
DRAMA_MOVIE_WHITELIST = {
    "cctv", "drama", "movie", "影迷", "电影", "影院", "影视", "tvb", "翡翠", "明珠", "j2", "tvb plus",
    "tvbmytvsuper", "mytv super", "美亞", "mei ah", "天映", "catchplay", "astro", "华丽台", "aod", "欢喜台", "aec", "兆烽台", "喜悅台", "cinema", "8tv", "小太阳",
    "disney", "netflix", "iqiyi", "愛奇藝", "viu", "viutv", "viu tv", "hotstar", "viki"
}

# =========================
# EPG 映射 - 加 OTT 頻道
# =========================
EPG_ID_MAP = {
    "翡翠台": "Jade.hk",
    "明珠台": "Pearl.hk",
    "J2": "J2.hk",
    "TVB Plus": "TVBPlus.hk",
    "無綫新聞台": "TVBNews.hk",
    "美亞電影台": "MeiAh.hk",
    "ViuTV": "ViuTV.hk",
    "Disney+": "DisneyPlus",
    "iQIYI": "iQIYI",
    "Netflix": "Netflix",
    "Hotstar": "Hotstar",
    "Viki": "Viki"
}

# =========================
# 強制添加 TVB myTV SUPER + OTT 頻道（多源備份）
# 注意：Disney+/Netflix/Hotstar/Viki/iQIYI 官方無免費 m3u 源，僅聚合備份（灰色，易失效）
# =========================
OTT_FORCED_SOURCES = {
    "翡翠台": [  # TVB myTV SUPER 主頻道
        "https://edge6a.v2h-cdn.com/jade/jade.stream/chunklist.m3u8",
        "http://iptv.tvfix.org/hls/jade.m3u8",
        "http://php.jdshipin.com/TVOD/iptv.php?id=fct",
        "http://cdn.132.us.kg/live/fct4k/stream.m3u8"
    ],
    "明珠台": [
        "http://iptv.tvfix.org/hls/pearl.m3u8",
        "http://php.jdshipin.com/TVOD/iptv.php?id=mz"
    ],
    "J2": [
        "http://iptv.tvfix.org/hls/j2.m3u8",
        "http://php.jdshipin.com/TVOD/iptv.php?id=j2"
    ],
    "美亞電影台": [  # Mei Ah Drama/Movie
        "http://50.7.161.82:8278/streams/d/meiya_pye/playlist.m3u8",
        "http://iptv.tvfix.org/hls/mydy2.m3u8",
        "http://198.16.64.10:8278/meiyamovie_twn/playlist.m3u8"
    ],
    "ViuTV": [
        "http://iptv.tvfix.org/hls/viutv.m3u8",
        "http://php.jdshipin.com/TVOD/iptv.php?id=viutv"
    ],
    "Disney+": [  # 僅聚合備份，無官方免費源
        "http://50.7.161.82:8278/streams/d/disney/playlist.m3u8",  # 測試用
        "http://iptv.tvfix.org/hls/disney.m3u8"  # 可能失效
    ],
    "Netflix": [  # 僅聚合備份，無官方免費源
        "http://50.7.161.82:8278/streams/d/netflix/playlist.m3u8",  # 測試用
        "http://iptv.tvfix.org/hls/netflix.m3u8"  # 可能失效
    ],
    "Hotstar": [
        "http://50.7.161.82:8278/streams/d/hotstar/playlist.m3u8",
        "http://iptv.tvfix.org/hls/hotstar.m3u8"
    ],
    "Viki": [
        "http://50.7.161.82:8278/streams/d/viki/playlist.m3u8",
        "http://iptv.tvfix.org/hls/viki.m3u8"
    ],
    "iQIYI": [  # 愛奇藝
        "http://50.7.161.82:8278/streams/d/iqiyi/playlist.m3u8",
        "http://iptv.tvfix.org/hls/iqiyi.m3u8"
    ]
}

# =========================
# 工具函數（保持原樣）
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
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False

def detect_quality(url: str) -> int:
    u = url.lower()
    if "2160" in u or "4k" in u:
        return 4
    if "1080" in u:
        return 3
    if "720" in u:
        return 2
    return 1

def get_epg_id(name: str) -> str:
    for k, v in EPG_ID_MAP.items():
        if k.lower() in name.lower():
            return v
    return ""

def get_logo(epg_id: str) -> str:
    if epg_id:
        return f"https://raw.githubusercontent.com/fanmingming/live/main/tv/{epg_id}.png"
    return ""

# =========================
# 下載 & 讀取 M3U
# =========================
print("⬇️ 下载源文件...")
resp = requests.get(M3U_SOURCE_URL, timeout=15)
resp.raise_for_status()
with open(INPUT_FILE, "w", encoding="utf-8") as f:
    f.write(resp.text)

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
    lines = [l.strip() for l in f if l.strip()]

channels = []
i = 0
while i < len(lines) - 1:
    if lines[i].startswith("#EXTINF"):
        channels.append((lines[i], lines[i + 1]))
        i += 2
    else:
        i += 1

# =========================
# 聚合 + 过滤 + 探活
# =========================
all_channels = defaultdict(list)

for extinf, url in channels:
    m = re.search(r",(.+)$", extinf)
    if not m:
        continue
    name = m.group(1).strip()
    if is_ad_or_shop(name):
        continue
    if not is_stream_alive(url):
        continue
    all_channels[name].append(url)

# =========================
# 強制添加 OTT 頻道（TVB myTV SUPER + Disney+ 等）
# =========================
for name, forced_urls in OTT_FORCED_SOURCES.items():
    if forced_urls:
        existing = all_channels.get(name, [])
        combined = list(set(forced_urls + existing))
        alive = [u for u in combined if is_stream_alive(u)]
        if alive:
            all_channels[name] = alive
            print(f"✅ 添加 OTT 頻道: {name} ({len(alive)} 條備份)")

# =========================
# 生成 final（多源 + 穩定優先）
# =========================
final = []

for name, urls in all_channels.items():
    epg_id = get_epg_id(name)
    logo = get_logo(epg_id)
    urls.sort(key=detect_quality, reverse=True)
    multi_url = "|".join(urls) if len(urls) > 1 else urls[0]
    q = max(detect_quality(u) for u in urls) if urls else 1
    label = {4: "4K", 3: "1080P", 2: "720P", 1: "HD"}[q]

    ext = f'#EXTINF:-1 tvg-name="{name}"'
    if epg_id:
        ext += f' tvg-id="{epg_id}"'
    if logo:
        ext += f' tvg-logo="{logo}"'
    ext += f",{name} | {label}"

    # 加註釋
    if any(k in name.lower() for k in ["disney", "netflix", "hotstar", "viki", "iqiyi", "viu", "mytv super", "美亞"]):
        ext += "  # OTT 頻道 - 建議合法訂閱 + VPN；源灰色易失效"

    final.append((name, q, ext, multi_url))

# =========================
# 排序 + 編號
# =========================
final.sort(key=lambda x: (x[0], -x[1]))

output = []
chno = 1
for _, _, ext, url in final:
    ext = ext.replace("#EXTINF:-1 ", f'#EXTINF:-1 tvg-chno="{chno}" ')
    output.append((ext, url))
    chno += 1

# =========================
# 寫出
# =========================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for ext, url in output:
        f.write(ext + "\n")
        f.write(url + "\n")

print(f"✅ 完成：{len(output)} 條頻道 → {OUTPUT_FILE}")
print("提示：Disney+/Netflix/Hotstar/Viki/iQIYI 無官方免費源，僅聚合備份（灰色，易失效）；建議合法訂閱官方 App + VPN。TVB myTV SUPER / ViuTV / 美亞 源較穩，但仍需定期更新。")