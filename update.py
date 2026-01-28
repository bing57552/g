import os
import re
import json
import time
import requests
from collections import defaultdict
from urllib.parse import urlparse

# =====================
# 基础配置
# =====================
TIMEOUT = 8
CHECK_BYTES = 1024 * 256
MAX_SOURCES_PER_CHANNEL = 5

SOURCE_POOL = "source_pool.txt"
OUTPUT_FILE = "output_best.m3u"
HEALTH_FILE = "stream_health.json"

# =====================
# 工具函数
# =====================
def fetch_text(url):
    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200 and "#EXTM3U" in r.text:
            return r.text
    except:
        pass
    return ""

def is_stream_alive(url):
    try:
        r = requests.get(url, stream=True, timeout=TIMEOUT)
        for _ in r.iter_content(chunk_size=CHECK_BYTES):
            return True
    except:
        pass
    return False

def score_url(url):
    score = 0
    if "4k" in url.lower():
        score += 30
    if "1080" in url.lower():
        score += 20
    if url.startswith("https"):
        score += 10
    if ".m3u8" in url:
        score += 10
    return score

# =====================
# 解析 m3u
# =====================
def parse_m3u(content):
    lines = content.splitlines()
    channels = []
    current = None

    for line in lines:
        if line.startswith("#EXTINF"):
            current = line
        elif line and not line.startswith("#") and current:
            channels.append((current, line))
            current = None
    return channels

def extract_meta(extinf):
    name = re.search(r",(.+)", extinf)
    tvg = re.search(r'tvg-id="([^"]*)"', extinf)
    return (
        name.group(1).strip() if name else "",
        tvg.group(1).strip() if tvg else ""
    )

# =====================
# 主逻辑
# =====================
def main():
    # 1. 读取健康记录
    health = {}
    if os.path.exists(HEALTH_FILE):
        with open(HEALTH_FILE, "r", encoding="utf-8") as f:
            health = json.load(f)

    # 2. 拉取所有源
    pool_urls = []
    if os.path.exists(SOURCE_POOL):
        with open(SOURCE_POOL, "r", encoding="utf-8") as f:
            pool_urls = [l.strip() for l in f if l.strip()]

    all_channels = defaultdict(list)

    for src in pool_urls:
        text = fetch_text(src)
        if not text:
            continue
        for extinf, url in parse_m3u(text):
            name, tvg = extract_meta(extinf)
            if not name:
                continue
            all_channels[(name, tvg)].append((extinf, url))

    # 3. 探测 & 评分
    final_channels = []

    for (name, tvg), items in all_channels.items():
        scored = []
        for extinf, url in items:
            alive = is_stream_alive(url)
            health[url] = {
                "alive": alive,
                "last_check": int(time.time())
            }
            if alive:
                scored.append((score_url(url), extinf, url))

        if not scored:
            continue

        scored.sort(reverse=True)
        for s in scored[:MAX_SOURCES_PER_CHANNEL]:
            final_channels.append((s[1], s[2]))

    # 4. 输出 m3u
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, url in final_channels:
            f.write(extinf + "\n")
            f.write(url + "\n")

    # 5. 保存健康状态
    with open(HEALTH_FILE, "w", encoding="utf-8") as f:
        json.dump(health, f, indent=2, ensure_ascii=False)

    print("✅ IPTV 自动运维完成")

if __name__ == "__main__":
    main()