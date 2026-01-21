import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= 基本配置 =================
TIMEOUT = 10          # 连接超时（秒）
THREADS = 20          # 并发测速线程
MAX_KEEP = 3          # 每个频道最多保留几个源
OUT_FILE = "all.m3u"

EPG_URL = "https://epg.112114.xyz/pp.xml"

# 购物 / 广告过滤
BLOCK_KEYWORDS = [
    "购物", "广告", "导购", "直销", "带货",
    "SHOP", "Shopping", "TV Mall"
]

# 频道名统一（重点）
NAME_MAP = {
    "Channel8": "阳光卫视",
    "Channel 8": "阳光卫视",
    "SUN TV": "阳光卫视",
    "Sun TV": "阳光卫视",
    "SUNTv": "阳光卫视",
}

# ================= 工具函数 =================
def normalize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"(HD|高清|1080P|4K)", "", name, flags=re.I)
    name = name.replace("(", "").replace(")", "")
    name = NAME_MAP.get(name, name)
    return name.strip()

def blocked(name: str) -> bool:
    return any(k.lower() in name.lower() for k in BLOCK_KEYWORDS)

def test_speed(url: str):
    try:
        start = time.time()
        r = requests.get(url, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        for _ in r.iter_content(chunk_size=8192):
            break
        r.close()
        return time.time() - start
    except:
        return None

# ================= 读取所有 m3u =================
channels = {}  # {频道名: set(urls)}

for root, _, files in os.walk("."):
    for file in files:
        if file.endswith(".m3u") and file != OUT_FILE:
            path = os.path.join(root, file)
            with open(path, encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()

            current = None
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    name = line.split(",")[-1]
                    name = normalize_name(name)
                    if blocked(name):
                        current = None
                        continue
                    current = name
                    channels.setdefault(current, set())
                elif line.startswith("http") and current:
                    channels[current].add(line)

# ================= 自动测速 + 排序 =================
def speed_sort(urls: set):
    speeds = []
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        futures = {pool.submit(test_speed, u): u for u in urls}
        for f in as_completed(futures):
            u = futures[f]
            s = f.result()
            if s is not None:
                speeds.append((s, u))
    speeds.sort(key=lambda x: x[0])
    return [u for _, u in speeds[:MAX_KEEP]]

final_channels = {}
for name, urls in channels.items():
    fast = speed_sort(urls)
    if fast:
        final_channels[name] = fast

# ================= 输出 all.m3u =================
with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n')
    for name, urls in final_channels.items():
        f.write(f"#EXTINF:-1,{name}\n")
        for u in urls:
            f.write(u + "\n")

print(f"✅ 完成：{len(final_channels)} 个频道（自动测速 + 多源合并）")