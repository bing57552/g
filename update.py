import os
import re
import json
import time
import requests
from collections import defaultdict

# =====================
# 基础配置
# =====================
TIMEOUT = 8
CHECK_BYTES = 1024 * 256
MAX_SOURCES_PER_CHANNEL = 5
# =====================
# 精准过滤：购物 / 广告台
# =====================
SHOPPING_CHANNELS = {
    "hsn", "home shopping network", "qvc us", "shophq",
    "jewelry television", "jtv", "the shopping channel", "tsc",
    "qvc uk", "qvc germany", "qvc italy", "qvc france",
    "hse24", "hse extra", "ideal world", "jml direct",
    "央广购物", "家有购物", "好易购", "优购物", "快乐购",
    "东森购物", "momo购物", "momo 购物台", "viva购物", "森森购物",
    "shop channel japan", "qvc japan",
    "gs shop", "cj o shopping", "lotte homeshopping",
    "ns home shopping", "hyundai home shopping",
    "star cj alive", "homeshop18", "naaptol",
    "dubai shopping", "gulf shopping",
    "tvsn", "openshop"
}

AD_CHANNEL_KEYWORDS = {
    "advertising", "ad channel", "promo", "promotion",
    "campaign", "marketing", "classifieds"
}
SOURCE_POOL = "source_pool.txt"
OUTPUT_FILE = "output_best.m3u"
HEALTH_FILE = "stream_health.json"

# EPG（观感提升核心）
EPG_URL = "https://epg.112114.xyz/pp.xml"

# 广告 / 购物台过滤（安全版）
BLOCK_KEYWORDS = ["购物", "广告", "导购"]

# 频道优先级（越小越靠前）
CHANNEL_PRIORITY = [
    ("CCTV", 0),
    ("央视", 0),

    ("卫视", 10),

    ("凤凰", 20),
    ("翡翠", 21),
    ("明珠", 22),

    ("Astro", 30),
    ("CHC", 31),

    ("TVB", 40),
    ("myTV", 41),

    ("八大", 50),
    ("gtv", 51),

    ("美亚", 60),
    ("电影", 61),

    ("Disney", 70),
    ("Netflix", 71),
]

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
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, stream=True, timeout=TIMEOUT, headers=headers)

        ct = r.headers.get("Content-Type", "").lower()
        if "text/html" in ct:
            return False

        size = 0
        start = time.time()
        for chunk in r.iter_content(chunk_size=8192):
            if not chunk:
                continue
            size += len(chunk)
            if size >= CHECK_BYTES:
                return True
            if time.time() - start > 3:
                return False
    except:
        return False

    return False

def score_url(url):
    u = url.lower()
    score = 0
    if "4k" in u: score += 40
    if "2160" in u: score += 40
    if "1080" in u: score += 25
    if u.startswith("https"): score += 10
    if ".m3u8" in u: score += 10
    return score

def channel_sort_key(name):
    for k, p in CHANNEL_PRIORITY:
        if k in name:
            return p
    return 999

# =====================
# M3U 解析
# =====================
def parse_m3u(content):
    lines = content.splitlines()
    res, cur = [], None
    for l in lines:
        if l.startswith("#EXTINF"):
            cur = l
        elif l and not l.startswith("#") and cur:
            res.append((cur, l))
            cur = None
    return res

def extract_meta(extinf):
    name = re.search(r",(.+)", extinf)
    tvg = re.search(r'tvg-id="([^"]*)"', extinf)
    return name.group(1).strip(), tvg.group(1).strip() if tvg else ""

# =====================
# 源池
# =====================
def load_sources():
    urls = []
    if not os.path.exists(SOURCE_POOL):
        return urls
    with open(SOURCE_POOL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                urls.append(line)
    return list(set(urls))

# =====================
# 主逻辑
# =====================
def main():
    # 1. health 读取
    health = {}
    if os.path.exists(HEALTH_FILE):
        with open(HEALTH_FILE, "r", encoding="utf-8") as f:
            health = json.load(f)

    all_channels = defaultdict(list)
    pool_urls = load_sources()

    # 2. 拉取所有源
    for src in pool_urls:
        text = fetch_text(src)
        if not text:
            continue
        for extinf, url in parse_m3u(text):
            name, tvg = extract_meta(extinf)
            if not name:
                continue
            if any(k in name for k in BLOCK_KEYWORDS):
                continue
            all_channels[(name, tvg)].append((extinf, url))

    final = []

    # 3. 探测 + 评分
    for (name, tvg), items in all_channels.items():
        scored = []
        for extinf, url in items:
            alive = is_stream_alive(url)
            health[url] = {
                "alive": alive,
                "last": int(time.time())
            }
            if alive:
                scored.append((score_url(url), extinf, url))

        scored.sort(reverse=True)

        # 保底：避免频道消失
        if not scored:
            for extinf, url in items:
                if health.get(url, {}).get("alive"):
                    final.append((extinf, url))
                    break
            continue

        for s in scored[:MAX_SOURCES_PER_CHANNEL]:
            final.append((s[1], s[2]))

    # 4. 排序
    final.sort(key=lambda x: channel_sort_key(x[0]))

    # 5. 输出 M3U（自动 EPG）
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(
    '#EXTM3U ' +
    ' '.join([f'x-tvg-url="{u}"' for u in EPG_URLS]) +
    f' tvg-logo="{LOGO_URL}"\n'
)
        for extinf, url in final:
            f.write(extinf + "\n")
            f.write(url + "\n")

    # 6. 保存 health
    with open(HEALTH_FILE, "w", encoding="utf-8") as f:
        json.dump(health, f, indent=2, ensure_ascii=False)

    print("✅ IPTV 全自动运维完成（终极稳定版）")

if __name__ == "__main__":
    main()