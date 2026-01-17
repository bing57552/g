import os
import requests
import time

# 过滤购物台关键词
BLOCK_KEYWORDS = ["购物", "shop", "momo", "东森购物", "年代购物", "tvbs欢乐购物"]

# 超时时间（秒）
TIMEOUT = 3

# -------------------------------
# 中文频道识别（电影 / 电视剧）
# -------------------------------

def is_chinese_channel(title):
    keywords = [
        "中文","华语","电影","戏剧","影视","影","剧",
        "港","澳","台","星河","天映","凤凰",
        "Astro","AOD","AEC","QJ",
        "龙华","靖天","纬来","东森","POPC"
    ]
    return any(k in title for k in keywords)

def is_movie_channel(title):
    keywords = ["电影","Movie","Cinema","影","天映","龙祥","好莱坞","影迷"]
    return any(k in title for k in keywords)

def is_drama_channel(title):
    keywords = ["戏剧","剧","Drama","AOD","双星","欢喜","AEC","龙华戏剧","靖天戏剧"]
    return any(k in title for k in keywords)

# -------------------------------
# 测速（返回延迟）
# -------------------------------

def test_url(url):
    """测试直播源是否可用 + 返回延迟（秒）"""
    try:
        start = time.time()
        r = requests.get(url, timeout=TIMEOUT)
        delay = time.time() - start
        if r.status_code == 200:
            return delay
    except:
        pass
    return None

# -------------------------------
# 每个频道只保留最快线路
# -------------------------------

def pick_fastest_per_channel(channels):
    """
    输入：[{title, url, ping}, ...]
    输出：每个频道只保留最快线路
    """
    best = {}
    for item in channels:
        title = item["title"].strip()
        if title not in best or item["ping"] < best[title]["ping"]:
            best[title] = item
    return list(best.values())

# -------------------------------
# 动态生成中文电影 / 电视剧总入口
# -------------------------------

def build_dynamic_cn_vod(all_channels_with_speed):
    """
    输入：测速后的频道列表
    输出：动态生成的中文电影 / 电视剧 m3u
    """

    # 1. 过滤中文 + 电影 / 电视剧频道
    filtered = [
        c for c in all_channels_with_speed
        if is_chinese_channel(c["title"]) and (
            is_movie_channel(c["title"]) or is_drama_channel(c["title"])
        )
    ]

    # 2. 去购物台
    bad_words = ["购物","导购","shop","sale","家居购物","购物台"]
    filtered = [c for c in filtered if not any(w in c["title"] for w in bad_words)]

    # 3. 每个频道只保留最快线路
    best = pick_fastest_per_channel(filtered)

    # 4. 输出 m3u
    lines = ["#EXTM3U\n"]
    for item in best:
        lines.append(f'#EXTINF:-1,{item["title"]}\n')
        lines.append(item["url"] + "\n")

    return lines

# -------------------------------
# 主流程：扫描 → 收集 → 测速 → 动态生成
# -------------------------------

def main():
    print("开始扫描所有 m3u 文件...\n")

    all_channels = []

    # 1. 扫描当前目录所有 .m3u 文件
    for filename in os.listdir("."):
        if filename.endswith(".m3u"):
            print(f"读取：{filename}")
            with open(filename, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            current_title = ""
            for line in lines:
                line = line.strip()

                if line.startswith("#EXTINF"):
                    current_title = line.replace("#EXTINF:-1,", "").strip()
                    continue

                if line.startswith("http"):
                    url = line.strip()
                    all_channels.append({"title": current_title, "url": url})

    print(f"\n共收集频道：{len(all_channels)} 条\n")

    # 2. 测速
    print("开始测速...\n")
    all_channels_with_speed = []
    for item in all_channels:
        ping = test_url(item["url"])
        if ping is not None:
            item["ping"] = ping
            all_channels_with_speed.append(item)
            print(f"[OK] {item['title']}  延迟：{ping:.2f}s")
        else:
            print(f"[X] {item['title']}  不可用")

    print(f"\n可用频道：{len(all_channels_with_speed)} 条\n")

    # 3. 动态生成中文电影 / 电视剧总入口
    cn_vod_lines = build_dynamic_cn_vod(all_channels_with_speed)

    with open("cn_vod_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(cn_vod_lines)

    print("已生成：cn_vod_live.m3u\n")

    print("全部完成！")

if __name__ == "__main__":
    main()