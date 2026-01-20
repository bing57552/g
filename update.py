import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor

# 1. 核心频道关键词
KEYWORDS = ["Astro", "TVB", "翡翠", "myTV", "SUPER", "美亚", "Disney+", "Netflix", "GTV", "八大", "Pop", "CHC", "CatchPlay"]

def check_url(item):
    name_info, url = item
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'}
    try:
        start_time = time.time()
        # 增加超时到 10s 确保稳定
        with requests.get(url, headers=headers, timeout=10.0, stream=True) as r:
            if r.status_code == 200:
                chunk = next(r.iter_content(chunk_size=128*1024))
                speed = len(chunk) / 1024 / (time.time() - start_time)
                if speed > 200: 
                    return {"name": name_info, "url": url, "speed": speed}
    except:
        pass
    return None

def main():
    # 【最关键一步】：必须包含这 6 个链接，否则永远只有 3 个频道
    sources = [
    "https://raw.githubusercontent.com/Guovin/TV/gd/output/result.m3u",
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",
    "https://raw.githubusercontent.com/youshandefeiyang/IPTV/main/main.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/hk.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tw.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/my.m3u"
]


    temp_list = []
    print("正在获取源数据...")
    for s_url in sources:
        try:
            r = requests.get(s_url, timeout=15)
            lines = r.text.split('\n')
            for i in range(len(lines)):
                if "#EXTINF" in lines[i] and any(k.upper() in lines[i].upper() for k in KEYWORDS):
                    if i + 1 < len(lines) and lines[i+1].startswith('http'):
                        temp_list.append((lines[i], lines[i+1].strip()))
        except: continue

    print(f"找到备选频道 {len(temp_list)} 个，开始测速...")
    with ThreadPoolExecutor(max_workers=30) as executor:
        results = [res for res in executor.map(check_url, temp_list) if res]

    # 按速度排序，确保保留最快的
    results.sort(key=lambda x: x["speed"], reverse=True)

    final_output = ["#EXTM3U"]
    added_channels = set()

    for res in results:
        raw_name = res["name"].split(',')[-1].strip()
        # 只保留每个频道最快的一条
        if raw_name not in added_channels:
            region = ""
            if "hk.m3u" in res["url"]: region = "[HK]"
            elif "tw.m3u" in res["url"]: region = "[TW]"
            elif "my.m3u" in res["url"]: region = "[MY]"
            
            display_name = f"{raw_name} {region}".strip()
            final_output.append(f"#EXTINF:-1, {display_name}\n{res['url']}")
            added_channels.add(raw_name)

    # 只要有效频道超过 5 个就强制写入
    if len(added_channels) > 5:
        with open("all.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(final_output))
        print(f"✅ 更新完成！共保留 {len(added_channels)} 个唯一高清频道。")
    else:
        print("❌ 错误：抓取到的有效频道不足，请检查网络。")

if __name__ == "__main__":
    main()



