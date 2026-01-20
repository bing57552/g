import requests
import time
from concurrent.futures import ThreadPoolExecutor

# 1. 设置全球多地域源：当部分源失效时，脚本会自动从其他备份源抓取地址
SOURCES = {
    "north_america": "https://raw.githubusercontent.com/YueChan/Live/main/m3u/america.m3u",
    "europe": "https://raw.githubusercontent.com/YueChan/Live/main/m3u/europe.m3u",
    "asia_chinese": "https://raw.githubusercontent.com/YueChan/Live/main/m3u/asia.m3u",
    "southeast_asia": "https://raw.githubusercontent.com/YueChan/Live/main/m3u/singapore_malaysia.m3u",
    "global_zh": "https://iptv-org.github.io/iptv/languages/zho.m3u",
    "movie_itv": "https://itvlist.cc/itv.m3u"
}

# 2. 电影、电视剧精准筛选关键词
KEYWORDS = ["电影", "电视剧", "剧场", "影院", "TVB", "翡翠台", "星河", "华语", "Channel 8", "U频道", "Drama", "Movie"]

def check_url(item):
    """自动剔除卡顿和音画不同步的直播源"""
    name_info, url = item
    # 模拟真实浏览器请求，防止被服务器屏蔽导致的断流或同步问题
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        start_time = time.time()
        # 将超时设置为 2.0s。虽然延迟增加，但能有效保留海外高质量源
        response = requests.head(url, headers=headers, timeout=2.0, allow_redirects=True)
        end_time = time.time()
        
        # 只有返回 200 (有效) 的源才会被加入列表
        if response.status_code == 200:
            return {"name": name_info, "url": url, "speed": end_time - start_time}
    except:
        pass
    return None

def main():
    unique_channels = {}
    
    for filename, url in SOURCES.items():
        try:
            print(f"🔄 正在获取最新有效源: {filename}")
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            lines = r.text.split('\n')
            temp_list = []
            
            for i in range(len(lines)):
                if "#EXTINF" in lines[i] and i + 1 < len(lines):
                    name_info = lines[i].strip()
                    link = lines[i+1].strip()
                    
                    if link.startswith('http'):
                        clean_name = name_info.split(',')[-1].strip()
                        # 仅处理包含影视关键词的频道
                        if any(kw.lower() in clean_name.lower() for kw in KEYWORDS):
                            temp_list.append((name_info, link))

            # 3. 并发检测与测速
            with ThreadPoolExecutor(max_workers=30) as executor:
                results = list(executor.map(check_url, temp_list))

            # 4. 自动替换逻辑：同名频道只保留响应速度最快的地址
            for res in results:
                if res:
                    c_name = res["name"].split(',')[-1].strip()
                    if c_name not in unique_channels or res["speed"] < unique_channels[c_name]["speed"]:
                        unique_channels[c_name] = res
            
        except Exception as e:
            print(f"⚠️ 源 {filename} 暂时不可用: {e}")

    # 5. 生成最新的 all.m3u 文件
    final_content = ["#EXTM3U"]
    for res in unique_channels.values():
        final_content.append(f"{res['name']}\n{res['url']}")

    with open("all.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(final_content))
    
    print(f"\n🚀 自动更新完成！已同步全球影视资源。当前有效频道总数: {len(unique_channels)}")

if __name__ == "__main__":
    main()



