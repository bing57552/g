import os
import re
import time
import requests
import concurrent.futures
from collections import defaultdict

# ======================
# 配置区
# ======================
MAX_KEEP_PER_CHANNEL = 3
FAILED_CACHE_FILE = "failed_cache.txt"
LOGO_BASE_URL = "https://raw.githubusercontent.com/你的用户名/你的仓库/main/logo/"

if os.getenv("GITHUB_ACTIONS") == "true":
    TIMEOUT = 8
    MAX_WORKERS = 10
else:
    TIMEOUT = 10
    MAX_WORKERS = 20

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ======================
# 工具函数
# ======================
def clean_channel_name(name):
    name = re.sub(r"(高清|HD|FHD|4K|直播源?|在线|\(.*?\))", "", name, flags=re.I)
    return re.sub(r"\s+", " ", name).strip()

def detect_group(name):
    if "CCTV" in name:
        return "央视频道"
    if "卫视" in name:
        return "卫视频道"
    if any(x in name for x in ("翡翠", "明珠", "本港台", "香港")):
        return "港台频道"
    if any(x in name for x in ("东森", "中天", "三立")):
        return "台湾频道"
    if any(x in name for x in ("HBO", "FOX", "CNN")):
        return "海外频道"
    if "电影" in name:
        return "电影频道"
    return "其他"

def build_extinf(raw_extinf):
    name = raw_extinf.split(",")[-1]
    clean_name = clean_channel_name(name)
    group = detect_group(clean_name)
    tvg_id = clean_name
    logo = LOGO_BASE_URL + clean_name.replace(" ", "") + ".png"

    return (
        f'#EXTINF:-1 tvg-id="{tvg_id}" '
        f'tvg-name="{clean_name}" '
        f'tvg-logo="{logo}" '
        f'group-title="{group}",{clean_name}'
    )

# ======================
# 流检测
# ======================
def check_stream(extinf, url):
    start = time.time()
    try:
        r = requests.get(url, timeout=TIMEOUT, stream=True, headers=HEADERS)
        if r.status_code != 200:
            return None
        ctype = r.headers.get("Content-Type", "").lower()
        if not any(x in ctype for x in ("mpegurl", "video", "octet-stream", "mp2t")):
            return None
        latency = round(time.time() - start, 3)
        return extinf, url, latency
    except Exception:
        return None

# ======================
# 解析 m3u
# ======================
def parse_m3u(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip()]
    i = 0
    while i < len(lines) - 1:
        if lines[i].startswith("#EXTINF"):
            yield lines[i], lines[i + 1]
            i += 2
        else:
            i += 1

# ======================
# 主流程
# ======================
def main():
    tasks = []
    channel_map = defaultdict(list)

    for file in os.listdir("."):
        if not file.endswith(".m3u") or file.startswith("all-"):
            continue

        for raw_extinf, url in parse_m3u(file):
            if url.startswith("http"):
                unified_extinf = build_extinf(raw_extinf)
                tasks.append((unified_extinf, url))

    with concurrent.futures.ThreadPoolExecutor(MAX_WORKERS) as ex:
        futures = [ex.submit(check_stream, e, u) for e, u in tasks]
        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            if r:
                extinf, url, latency = r
                channel_map[extinf].append((latency, url))

    # 输出 all-fast.m3u
    with open("all-fast.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, sources in channel_map.items():
            for _, url in sorted(sources)[:MAX_KEEP_PER_CHANNEL]:
                f.write(extinf + "\n" + url + "\n")

    # 输出 all-full.m3u
    with open("all-full.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, sources in channel_map.items():
            for _, url in sorted(sources):
                f.write(extinf + "\n" + url + "\n")

    print("✅ 频道名 / 分组 / logo / tvg-id 已自动统一")

if __name__ == "__main__":
    main()
