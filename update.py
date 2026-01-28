import requests
import time
from collections import defaultdict

SOURCE_FILES = [
    "global_cn_4k1080p_multi.m3u",
    "hk.m3u",
    "movie.m3u",
    "all.m3u",
]

TIMEOUT = 5
RETRY = 3

def test_stream(url):
    score = 0
    try:
        for _ in range(RETRY):
            start = time.time()
            r = requests.get(
                url,
                timeout=TIMEOUT,
                stream=True,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if r.status_code != 200:
                return None
            ctype = r.headers.get("Content-Type", "").lower()
            if "video" in ctype or "mpegurl" in ctype or url.endswith(".m3u8"):
                delay = time.time() - start
                score += max(0, 5 - delay)
            else:
                return None
        return round(score, 2)
    except:
        return None

def parse_m3u(text):
    channels = defaultdict(list)
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            info = lines[i]
            name = info.split(",")[-1].strip()
            url = lines[i + 1].strip()
            channels[name].append((info, url))
            i += 2
        else:
            i += 1
    return channels

all_channels = defaultdict(list)

# 聚合
for file in SOURCE_FILES:
    try:
        with open(file, "r", encoding="utf-8") as f:
            parsed = parse_m3u(f.read())
        for name, items in parsed.items():
            all_channels[name].extend(items)
    except:
        pass

final_channels = {}

# 检测 + 排序 + 替换
for name, items in all_channels.items():
    valid = []
    for info, url in items:
        score = test_stream(url)
        if score:
            valid.append((score, info, url))

    valid.sort(key=lambda x: x[0], reverse=True)

    if valid:
        final_channels[name] = valid

# 输出
with open("ALL_IN_ONE.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for name, sources in final_channels.items():
        for _, info, url in sources:
            f.write(info + "\n")
            f.write(url + "\n")