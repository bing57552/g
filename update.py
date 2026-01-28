import os
import re
import json
import time
import requests
from collections import defaultdict

# =====================
# 基础配置（安全参数）
# =====================
TIMEOUT = 8                      # 请求超时
CHECK_BYTES = 256 * 1024          # 首包检测大小
MAX_SOURCES_PER_CHANNEL = 5       # 每频道最多保留源数量

SOURCE_POOL = "source_pool.txt"
OUTPUT_FILE = "output_best.m3u"
HEALTH_FILE = "stream_health.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (IPTV-Checker)"
}

# =====================
# 网络工具
# =====================
def fetch_text(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200 and "#EXTM3U" in r.text:
            return r.text
    except:
        pass
    return ""

def is_stream_alive(url):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT)
        for _ in r.iter_content(chunk_size=CHECK_BYTES):
            return True
    except:
        pass
    return False

# =====================
# 评分系统（不影响逻辑，只决定排序）
# =====================
def score_url(url):
    u = url.lower()
    score = 0

    if "4k" in u:
        score += 40
    if "1080" in u:
        score += 30
    if u.startswith("https"):
        score += 10
    if ".m3u8" in u:
        score += 10
    if "cdn" in u:
        score += 5
    if "live" in u:
        score += 5

    return score

# =====================
# m3u 解析
# =====================
def parse_m3u(content):
    lines = content.splitlines()
    items = []
    current = None

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            current = line
        elif line and not line.startswith("#") and current:
            items.append((current, line))
            current = None

    return items

def extract_meta(extinf):
    name_match = re.search(r",(.+)", extinf)
    tvg_match = re.search(r'tvg-id="([^"]*)"', extinf)

    name = name_match.group(1).strip() if name_match else ""
    tvg = tvg_match.group(1).strip() if tvg_match else ""

    return name, tvg

# =====================
# 主程序（核心逻辑）
# =====================
def main():
    # 1. 读取健康记录
    health = {}
    if os.path.exists(HEALTH_FILE):
        try:
            with open(HEALTH_FILE, "r", encoding="utf-8") as f:
                health = json.load(f)
        except:
            health = {}

    # 2. 读取源池
    if not os.path.exists(SOURCE_POOL):
        print("❌ source_pool.txt 不存在")
        return

    with open(SOURCE_POOL, "r", encoding="utf-8") as f:
        pool_urls = [l.strip() for l in f if l.strip()]

    all_channels = defaultdict(list)

    # 3. 聚合所有源
    for src in pool_urls:
        content = fetch_text(src)
        if not content:
            continue

        for extinf, url in parse_m3u(content):
            name, tvg = extract_meta(extinf)
            if not name:
                continue
            all_channels[(name, tvg)].append((extinf, url))

    # 4. 探测 + 排序
    final_output = []

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

        scored.sort(key=lambda x: x[0], reverse=True)

        for s in scored[:MAX_SOURCES_PER_CHANNEL]:
            final_output.append((s[1], s[2]))

    # 5. 输出最终 m3u
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, url in final_output:
            f.write(extinf + "\n")
            f.write(url + "\n")

    # 6. 保存健康状态
    with open(HEALTH_FILE, "w", encoding="utf-8") as f:
        json.dump(health, f, ensure_ascii=False, indent=2)

    print("✅ IPTV 自动运维完成")

if __name__ == "__main__":
    main()