import os
import requests
import time
# 测速函数：返回毫秒
def test_speed(url, timeout=3):
    try:
        start = time.time()
        r = requests.get(url, timeout=timeout, stream=True)
        r.close()
        end = time.time()
        return (end - start) * 1000  # 转换为毫秒
    except:
        return 99999  # 超时或失败
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
    lines = ["#EXTM3U\n"]
for idx, item in enumerate(best, start=1):
    number = f"{idx:03d}"  # 生成 001、002、003...
    title = f"{number} {item['title']}"
    lines.append(f'#EXTINF:-1,{title}\n')
    lines.append(item["url"] + "\n")

    return lines

# -------------------------------
# 主流程：扫描 → 收集 → 测速 → 动态生成
# -------------------------------
def generate_readme_and_html(total_channels,
                             movie_count,
                             drama_count,
                             hk_count,
                             tw_count,
                             oversea_count,
                             no_shopping_count):
    """自动生成 README.md 和 HTML 入口页（带二维码链接）"""

    repo_raw_base = "https://raw.githubusercontent.com/bing57552/IPTV/main"

    master_url = f"{repo_raw_base}/master.m3u"
    live_url = f"{repo_raw_base}/live.m3u"
    movie_url = f"{repo_raw_base}/movie.m3u"
    drama_url = f"{repo_raw_base}/drama.m3u"
    cn_vod_url = f"{repo_raw_base}/cn_vod_live.m3u"
    hk_url = f"{repo_raw_base}/hk.m3u"
    tw_url = f"{repo_raw_base}/tw.m3u"
    oversea_url = f"{repo_raw_base}/oversea.m3u"
    no_shopping_url = f"{repo_raw_base}/no-shopping.m3u"

    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def qr_link(url):
        return f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={url}"

    readme_lines = [
        "# IPTV 自动聚合系统\n\n",
        f"- 更新时间：`{now_str}`\n",
        f"- 频道总数：**{total_channels}**\n",
        f"- 电影频道：**{movie_count}**\n",
        f"- 电视剧频道：**{drama_count}**\n",
        f"- 香港频道：**{hk_count}**\n",
        f"- 台湾频道：**{tw_count}**\n",
        f"- 海外频道：**{oversea_count}**\n",
        f"- 去购物台频道：**{no_shopping_count}**\n\n",
        "## 远程订阅链接\n\n",
        f"- 总入口（推荐）：`{master_url}`\n",
        f"- 综合直播：`{live_url}`\n",
        f"- 电影频道：`{movie_url}`\n",
        f("- 电视剧频道：`{drama_url}`\n"),
        f("- 动态中文影视：`{cn_vod_url}`\n"),
        f("- 香港频道：`{hk_url}`\n"),
        f("- 台湾频道：`{tw_url}`\n"),
        f("- 海外频道：`{oversea_url}`\n"),
        f("- 去购物台：`{no_shopping_url}`\n\n"),
        "## 二维码订阅入口\n\n",
        f"### 总入口 master.m3u\n\n![master]({qr_link(master_url)})\n\n",
        f"### 动态中文影视 cn_vod_live.m3u\n\n![cn_vod]({qr_link(cn_vod_url)})\n\n",
        f"### 综合直播 live.m3u\n\n![live]({qr_link(live_url)})\n\n",
    ]

    with open("README.md", "w", encoding="utf-8") as f:
        f.writelines(readme_lines)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>IPTV 自动聚合入口</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#111; color:#eee; padding:20px; }}
h1,h2,h3 {{ color:#ffd166; }}
a {{ color:#4dabf7; }}
.card {{ border:1px solid #333; padding:15px; margin-bottom:15px; border-radius:8px; background:#1b1b1b; }}
.qr {{ margin-top:10px; }}
</style>
</head>
<body>
<h1>IPTV 自动聚合入口</h1>
<p>更新时间：{now_str}</p>
<ul>
  <li>频道总数：{total_channels}</li>
  <li>电影频道：{movie_count}</li>
  <li>电视剧频道：{drama_count}</li>
  <li>香港频道：{hk_count}</li>
  <li>台湾频道：{tw_count}</li>
  <li>海外频道：{oversea_count}</li>
  <li>去购物台频道：{no_shopping_count}</li>
</ul>

<div class="card">
  <h2>总入口（推荐）</h2>
  <p><a href="{master_url}">{master_url}</a></p>
  <div class="qr">
    <img src="{qr_link(master_url)}" alt="master.m3u" />
  </div>
</div>

<div class="card">
  <h2>动态中文影视</h2>
  <p><a href="{cn_vod_url}">{cn_vod_url}</a></p>
  <div class="qr">
    <img src="{qr_link(cn_vod_url)}" alt="cn_vod_live.m3u" />
  </div>
</div>

<div class="card">
  <h2>综合直播</h2>
  <p><a href="{live_url}">{live_url}</a></p>
  <div class="qr">
    <img src="{qr_link(live_url)}" alt="live.m3u" />
  </div>
</div>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("已生成：README.md 和 index.html（含二维码链接）")
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
total_channels = len(all_channels_with_speed)
    movie_count = len(movie_channels)
    drama_count = len(drama_channels)
    hk_count = len(hk_channels)
    tw_count = len(tw_channels)
    oversea_count = len(oversea_channels)
    no_shopping_count = len(no_shopping_channels)

    generate_readme_and_html(
        total_channels,
        movie_count,
        drama_count,
        hk_count,
        tw_count,
        oversea_count,
        no_shopping_count,
    )
    print("全部完成！")

if __name__ == "__main__":
    main()