# update.py

import requests

def fetch(url):
    try:
        return requests.get(url, timeout=10).text
    except:
        return ""

# 港澳台公开源（iptv-org）
HK = "https://iptv-org.github.io/iptv/regions/hk.m3u"
TW = "https://iptv-org.github.io/iptv/regions/tw.m3u"
MO = "https://iptv-org.github.io/iptv/regions/mo.m3u"

# 电影台（含 CATCHPLAY）
MOVIE = "https://iptv-org.github.io/iptv/categories/movies.m3u"

# 你的自定义频道（Astro + CATCHPLAY）
CUSTOM = """
#EXTINF:-1 tvg-name="Astro AOD 311" group-title="Astro", Astro AOD 311
http://50.7.161.82:8278/streams/d/AstroAOD/playlist.m3u8

#EXTINF:-1 tvg-name="Astro 双星" group-title="Astro", Astro Shuang Xing
http://50.7.161.82:8278/streams/d/Shuangxing/playlist.m3u8

#EXTINF:-1 tvg-name="CATCHPLAY Movies" group-title="电影", CATCHPLAY 电影台
https://d3j7ofexbkpjkf.cloudfront.net/CH_CATCHPLAY/index.m3u8
"""

# 去除购物台关键词
BLOCK = ["购物", "購物", "Shop", "Mall", "家购", "momo", "东森购物"]

def clean(content):
    lines = content.splitlines()
    cleaned = []
    skip = False

    for line in lines:
        if line.startswith("#EXTINF"):
            skip = any(b in line for b in BLOCK)
        if not skip:
            cleaned.append(line)

    return "\n".join(cleaned)

def main():
    print("开始更新 live.m3u ...")

    # 抓取公开源
    hk = fetch(HK)
    tw = fetch(TW)
    mo = fetch(MO)
    movie = fetch(MOVIE)

    # 合并所有源
    merged = "#EXTM3U\n"
    merged += clean(hk) + "\n"
    merged += clean(tw) + "\n"
    merged += clean(mo) + "\n"
    merged += clean(movie) + "\n"
    merged += CUSTOM

    # 写入文件
    with open("live.m3u", "w", encoding="utf-8") as f:
        f.write(merged)

    print("更新完成！")

if __name__ == "__main__":
    main()import os
import requests

# 你要抓取直播源的基础地址（你只需要改这里）
BASE_URL = "https://example.com/"   # 例如 https://iptv-source.com/

def fetch_source(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ 抓取失败: {url} → {e}")
        return None

def main():
    print("🚀 自动扫描所有 .m3u 文件并更新...\n")

    # 自动扫描仓库目录下所有 .m3u 文件
    for filename in os.listdir("."):
        if filename.endswith(".m3u"):
            source_url = BASE_URL + filename
            print(f"🔄 正在更新：{filename}")
            content = fetch_source(source_url)

            if content:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ 更新成功：{filename}\n")
            else:
                print(f"⚠️ 跳过：{filename}（抓取失败）\n")

    print("🎉 所有直播源更新完成。")

if __name__ == "__main__":
    main()import requests

def fetch(url):
    try:
        return requests.get(url, timeout=10).text
    except:
        return ""

# 公开源（iptv-org）
TW_MOVIE = "https://iptv-org.github.io/iptv/languages/zho.m3u"

# 你的自定义频道（Astro + CATCHPLAY）
CUSTOM = """
#EXTINF:-1 tvg-name="Astro AOD 311" group-title="Astro", Astro AOD 311
http://50.7.161.82:8278/streams/d/AstroAOD/playlist.m3u8
#EXTINF:-1 tvg-name="Astro 双星" group-title="Astro", Astro Shuang Xing
http://50.7.161.82:8278/streams/d/Shuangxing/playlist.m3u8
#EXTINF:-1 tvg-name="CATCHPLAY Movies" group-title="电影", CATCHPLAY 电影台
https://d3j7ofexbkpjkf.cloudfront.net/CH_CATCHPLAY/index.m3u8
"""

# 去除购物台关键词
BLOCK = ["购物", "購物", "Shop", "Shopping", "Mall", "家购", "momo", "东森购物"]

def remove_shopping(lines):
    return "\n".join([l for l in lines.split("\n") if not any(b in l for b in BLOCK)])

def save(name, content):
    with open(name, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n" + content)

def main():
    tw = fetch(TW_MOVIE)
    merged = tw + "\n" + CUSTOM

    clean = remove_shopping(merged)

    save("live.m3u", clean)
    save("movie.m3u", clean)
    save("hk.m3u", clean)
    save("tw.m3u", clean)
    save("oversea.m3u", clean)
    save("no-shopping.m3u", clean)

if __name__ == "__main__":
    main()
