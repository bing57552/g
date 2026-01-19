#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= 基本配置 =================
TIMEOUT = 6
THREADS = 30
MAX_SOURCES = 4            # 每频道最多保留源数
OUTPUT = "live.m3u"
STATS_FILE = "stats.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 IPTV-Private"
}

# ================= 正则 =================
ZH_RE = re.compile(r"[\u4e00-\u9fa5]")
CLEAN_RE = re.compile(r"(HD|高清|超清|1080P|720P|测试|备用|\s+)", re.I)

# ================= 工具 =================
def is_chinese(text):
    return bool(ZH_RE.search(text))


def normalize_name(name):
    name = CLEAN_RE.sub("", name).strip()
    name = name.replace("＋", "+").replace("CCTV", "CCTV-")
    name = re.sub(r"CCTV-(\d)", r"CCTV-\1", name)
    return name


def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


# ================= M3U =================
def scan_m3u_files():
    return [f for f in os.listdir(".") if f.endswith(".m3u") and f != OUTPUT]


def parse_m3u(file):
    items = []
    name = None
    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#EXTINF"):
                name = line.split(",")[-1].strip()
            elif line.startswith("http"):
                if name:
                    items.append((name, line))
                name = None
    return items


# ================= 质量检测 =================
def test_source(task):
    name, url = task
    try:
        start = time.time()
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        if r.status_code != 200:
            return None

        first_chunk = None
        size = 0
        read_start = time.time()

        for chunk in r.iter_content(chunk_size=4096):
            if not chunk:
                continue

            now = time.time()
            if first_chunk is None:
                first_chunk = now - start

            size += len(chunk)
            if now - read_start > 10:
                break

        if first_chunk is None:
            return None

        duration = time.time() - start
        bitrate = (size * 8) / duration / 1000  # kbps

        # 硬性淘汰条件
        if first_chunk > 1.5 or bitrate < 1500:
            return None

        container = "ts" if ".ts" in url or ".flv" in url else "hls"

        return {
            "name": name,
            "url": url,
            "first": round(first_chunk, 2),
            "bitrate": int(bitrate),
            "container": container
        }

    except:
        return None


# ================= 谁稳谁上评分 =================
def calc_score(stat):
    total = stat["ok"] + stat["fail"]
    if total == 0:
        return 0

    success = stat["ok"] / total
    score = success * 60

    # 首包
    if stat["avg_first"] <= 0.8:
        score += 20
    elif stat["avg_first"] <= 1.2:
        score += 15
    elif stat["avg_first"] <= 1.5:
        score += 10

    # 码率
    if stat["avg_bitrate"] >= 3000:
        score += 15
    elif stat["avg_bitrate"] >= 2000:
        score += 10
    elif stat["avg_bitrate"] >= 1500:
        score += 5

    # 最近成功
    if time.time() - stat["last_ok"] < 3600:
        score += 5

    return round(score, 1)


# ================= 主流程 =================
def main():
    print("🚀 IPTV『谁稳谁上』终极版启动")

    stats = load_stats()
    pool = {}

    # 收集源
    for file in scan_m3u_files():
        for raw, url in parse_m3u(file):
            if not is_chinese(raw):
                continue
            name = normalize_name(raw)
            pool.setdefault(name, set()).add(url)

    # 测试
    results = {}
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = [
            ex.submit(test_source, (name, url))
            for name, urls in pool.items()
            for url in urls
        ]

        for f in as_completed(futures):
            r = f.result()
            if not r:
                continue
            results.setdefault(r["name"], []).append(r)

    # 更新统计
    for name, sources in results.items():
        stats.setdefault(name, {})
        for s in sources:
            u = s["url"]
            stat = stats[name].setdefault(u, {
                "ok": 0,
                "fail": 0,
                "avg_first": s["first"],
                "avg_bitrate": s["bitrate"],
                "last_ok": 0
            })
            stat["ok"] += 1
            stat["avg_first"] = (stat["avg_first"] + s["first"]) / 2
            stat["avg_bitrate"] = (stat["avg_bitrate"] + s["bitrate"]) / 2
            stat["last_ok"] = time.time()

    # 排序 & 输出
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        idx = 1

        for name in sorted(stats.keys()):
            ranked = []
            for url, stat in stats[name].items():
                score = calc_score(stat)
                if score > 0:
                    ranked.append((score, url))

            if not ranked:
                continue

            ranked.sort(reverse=True)
            ranked = ranked[:MAX_SOURCES]

            f.write(f"#EXTINF:-1,{idx}. {name}\n")
            for _, url in ranked:
                f.write(url + "\n")
            idx += 1

    save_stats(stats)
    print("✅ 完成：主源 / 备用源 已动态生成")
    print("📺 TVBox / iOTV 自动切换生效")


if __name__ == "__main__":
    main()