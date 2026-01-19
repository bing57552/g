import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

TIMEOUT = 3
MAX_WORKERS = 20


# ========================
# 工具函数
# ========================

def is_valid_and_speed(url):
    try:
        start = time.time()
        r = requests.get(url, timeout=TIMEOUT, stream=True)
        r.close()
        speed = int((time.time() - start) * 1000)
        return True, speed
    except:
        return False, 99999


def read_m3u(filename):
    channels = []
    name = None

    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#EXTINF"):
                name = line.split(",")[-1].strip()
            elif line.startswith("http") and name:
                channels.append({
                    "name": name,
                    "url": line,
                    "source": filename
                })
                name = None
    return channels


def classify(name):
    n = name.lower()
    if "港" in n or "hk" in n:
        return "hk"
    if "台" in n or "tw" in n:
        return "tw"
    if "电影" in n or "movie" in n:
        return "movie"
    if "海外" in n or "oversea" in n:
        return "oversea"
    if "购物" in n:
        return "no-shopping"
    return "other"


def write_m3u(filename, channels):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            f.write(f"#EXTINF:-1,{ch['name']}\n")
            f.write(f"{ch['url']}\n")


# ========================
# 主逻辑
# ========================

def main():
    print("🔍 扫描 m3u 文件...")

    m3u_files = [f for f in os.listdir(".") if f.endswith(".m3u")]

    if not m3u_files:
        print("❌ 未发现 m3u 文件，安全退出")
        return

    all_channels = []

    for f in m3u_files:
        print(f"📂 读取 {f}")
        all_channels.extend(read_m3u(f))

    print(f"📺 读取频道总数：{len(all_channels)}")

    valid_channels = []

    print("⚡ 并发测速中...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_map = {
            pool.submit(is_valid_and_speed, ch["url"]): ch
            for ch in all_channels
        }

        for future in as_completed(future_map):
            ch = future_map[future]
            ok, speed = future.result()
            if ok:
                ch["speed"] = speed
                valid_channels.append(ch)

    valid_channels.sort(key=lambda x: x["speed"])

    print(f"✅ 可用频道：{len(valid_channels)}")

    # ========================
    # 分类
    # ========================

    categories = {
        "hk": [],
        "tw": [],
        "movie": [],
        "oversea": [],
        "no-shopping": [],
        "other": []
    }

    for ch in valid_channels:
        categories[classify(ch["name"])].append(ch)

    # ========================
    # 输出 m3u
    # ========================

    write_m3u("cn_vod_live.m3u", valid_channels)

    for k, v in categories.items():
        if v:
            write_m3u(f"{k}.m3u", v)

    # ========================
    # README
    # ========================

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# IPTV 自动更新（增强版）\n\n")
        f.write(f"- 输入源文件：{len(m3u_files)}\n")
        f.write(f"- 原始频道：{len(all_channels)}\n")
        f.write(f"- 可用频道：{len(valid_channels)}\n\n")
        f.write("## 分类统计\n")
        for k, v in categories.items():
            f.write(f"- {k}: {len(v)}\n")
        f.write("\n## 输出文件\n")
        f.write("- cn_vod_live.m3u\n")
        for k in categories:
            f.write(f"- {k}.m3u\n")

    print("🎉 全部完成！")


# ========================
# 入口
# ========================

if __name__ == "__main__":
    main()