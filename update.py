import os
import re
import json
import time
import requests
from collections import defaultdict

TIMEOUT = 8
CHECK_BYTES = 1024 * 256
MAX_SOURCES_PER_CHANNEL = 5

SOURCE_POOL = "source_pool.txt"
OUTPUT_FILE = "output_best.m3u"
HEALTH_FILE = "stream_health.json"

# ---------------------
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
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Icy-MetaData": "1"
        }
        r = requests.get(url, stream=True, timeout=TIMEOUT, headers=headers)
        start = time.time()
        size = 0

        ct = r.headers.get("Content-Type", "").lower()
        if "text/html" in ct:
            return False

        for chunk in r.iter_content(chunk_size=8192):
            if not chunk:
                continue
            size += len(chunk)

            # 真正拉到 TS 数据
            if size >= CHECK_BYTES:
                return True

            # 超时直接判失败
            if time.time() - start > 3:
                return False
    except:
        return False

    return False

def score_url(url):
    score = 0
    u = url.lower()
    if "4k" in u: score += 30
    if "1080" in u: score += 20
    if u.startswith("https"): score += 10
    if ".m3u8" in u: score += 10
    return score

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

# ---------------------
def load_sources():
    urls = []
    with open(SOURCE_POOL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line.startswith("source/") and os.path.exists(line):
                with open(line, "r", encoding="utf-8") as sf:
                    urls += [u.strip() for u in sf if u.strip()]
            else:
                urls.append(line)
    return list(set(urls))

# ---------------------
def main():
    health = {}
    if os.path.exists(HEALTH_FILE):
        with open(HEALTH_FILE, "r", encoding="utf-8") as f:
            health = json.load(f)

    all_channels = defaultdict(list)
    pool_urls = load_sources()

    for src in pool_urls:
        text = fetch_text(src)
        if not text:
            continue
        for extinf, url in parse_m3u(text):
            name, tvg = extract_meta(extinf)
            if name:
                all_channels[(name, tvg)].append((extinf, url))

    final = []

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

        if not scored:
            # 保底：使用上一次成功的源，避免频道消失
            for extinf, url in items:
                if health.get(url, {}).get("alive"):
                    final.append((extinf, url))
                    break
            continue

        for s in scored[:MAX_SOURCES_PER_CHANNEL]:
            final.append((s[1], s[2]))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, url in final:
            f.write(extinf + "\n" + url + "\n")

    with open(HEALTH_FILE, "w", encoding="utf-8") as f:
        json.dump(health, f, indent=2, ensure_ascii=False)

    print("✅ IPTV 全自动运维完成")

if __name__ == "__main__":
    main()