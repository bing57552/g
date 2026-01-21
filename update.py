import os
import time
import json
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= 基本配置 =================
ROOT = os.path.dirname(os.path.abspath(__file__))

OUT_ALL = "all.m3u"
OUT_FAST = "all-fast.m3u"
OUT_FULL = "all-full.m3u"
FAIL_CACHE_FILE = "fail_cache.json"

IGNORE_FILES = {OUT_ALL, OUT_FAST, OUT_FULL}

TIMEOUT = 10
MAX_FAIL = 3
MAX_WORKERS = 15  # 并发测速数量（10~20 推荐）

# EPG
EPG_URL = "https://epg.112114.xyz/pp.xml.gz"

# 去购物 / 广告
BLOCK_KEYWORDS = [
    "购物", "导购", "广告", "促销", "带货", "直销",
    "SHOP", "Shopping", "TV Mall"
]

channels = {}

# ================= 失败缓存 =================
if os.path.exists(FAIL_CACHE_FILE):
    with open(FAIL_CACHE_FILE, "r", encoding="utf-8") as f:
        fail_cache = json.load(f)
else:
    fail_cache = {}


def save_fail_cache():
    with open(FAIL_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(fail_cache, f, ensure_ascii=False, indent=2)


# ================= 工具函数 =================
def is_blocked(name):
    return any(k.lower() in name.lower() for k in BLOCK_KEYWORDS)


def normalize_name(name: str) -> str:
    name = name.upper()
    name = re.sub(r"高清|HD|FHD|4K|频道", "", name)
    name = name.replace(" ", "").replace("－", "-")

    m = re.match(r"CCTV[-]?(\d+)", name)
    if m:
        return f"CCTV-{m.group(1)}"

    if name.endswith("卫视"):
        return name

    return name


def epg_id(name: str) -> str:
    m = re.match(r"CCTV-(\d+)", name)
    if m:
        return f"CCTV-{m.group(1)}"

    if name.endswith("卫视"):
        return name

    MAP = {
        "TVBS新闻": "TVBS新聞",
        "凤凰中文": "凤凰中文台",
        "凤凰资讯": "凤凰资讯台",
    }
    return MAP.get(name, name)


def test_speed(url):
    try:
        start = time.time()
        r = requests.get(url, stream=True, timeout=TIMEOUT)
        r.raise_for_status()
        for _ in r.iter_content(chunk_size=8192):
            break
        return time.time() - start
    except:
        return None


# ================= 解析 m3u =================
def parse_m3u(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip()]

    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF") and i + 1 < len(lines):
            url = lines[i + 1]
            raw_name = lines[i].split(",", 1)[-1].strip()

            if is_blocked(raw_name):
                i += 2
                continue

            name = normalize_name(raw_name)
            channels.setdefault(name, []).append({
                "url": url,
                "speed": None
            })
            i += 2
        else:
            i += 1


# ================= 扫描所有 m3u =================
for f in os.listdir(ROOT):
    if f.endswith(".m3u") and f not in IGNORE_FILES:
        parse_m3u(os.path.join(ROOT, f))


# ================= 并发测速 + 失败统计 =================
def speed_task(name, url):
    return name, url, test_speed(url)


tasks = []
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    for name, items in channels.items():
        for item in items:
            tasks.append(executor.submit(speed_task, name, item["url"]))

results = {}
for future in as_completed(tasks):
    name, url, speed = future.result()
    results.setdefault(name, {})[url] = speed


for name in list(channels.keys()):
    valid = []
    for item in channels[name]:
        url = item["url"]
        speed = results.get(name, {}).get(url)

        if speed is None:
            fail_cache[url] = fail_cache.get(url, 0) + 1
        else:
            fail_cache[url] = 0
            item["speed"] = speed
            valid.append(item)

    valid = [i for i in valid if fail_cache.get(i["url"], 0) < MAX_FAIL]

    if not valid:
        del channels[name]
    else:
        valid.sort(key=lambda x: x["speed"])
        channels[name] = valid

save_fail_cache()


# ================= 写入 m3u =================
def write_m3u(filename, mode):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n')
        for name, items in channels.items():
            tvg = epg_id(name)
            if mode == "fast":
                items = items[:1]

            for i in items:
                extinf = f'#EXTINF:-1 tvg-id="{tvg}" tvg-name="{tvg}",{name}'
                f.write(extinf + "\n")
                f.write(i["url"] + "\n")


write_m3u(OUT_ALL, "all")
write_m3u(OUT_FAST, "fast")
write_m3u(OUT_FULL, "full")

print(f"✅ 完成：{len(channels)} 个频道（并发测速 + EPG + 自愈）")