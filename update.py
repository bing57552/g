import requests
import time
from collections import defaultdict

SOURCE_FILES = [
    "global_cn_4k1080p_multi.m3u",
    "hk.m3u",
    "movie.m3u",
    "all.m3u",
]

TIMEOUT = 5  # 秒，够稳了

def speed_test(url):
    try:
        start = time.time()
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200:
            return round(time.time() - start, 2)
    except:
        pass
    return None  # 不可用

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

# 1️⃣ 读取并聚合
for file in SOURCE_FILES:
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = f.read()
        parsed = parse_m3u(data)
        for name, items in parsed.items():
            all_channels[name].extend(items)
    except:
        pass

# 2️⃣ 测速 + 排序
final_channels = {}

for name, items in all_channels.items():
    tested = []
    for info, url in items:
        t = speed_test(url)
        if t is not None:
            tested.append((t, info, url))

    # 按速度排序（越快越前）
    tested.sort(key=lambda x: x[0])

    if tested:
        final_channels[name] = tested

# 3️⃣ 输出最终 ALL_IN_ONE.m3u
with open("ALL_IN_ONE.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for name, sources in final_channels.items():
        for _, info, url in sources:
            f.write(info + "\n")
            f.write(url + "\n")