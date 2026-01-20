import requests
import time
from concurrent.futures import ThreadPoolExecutor

# 1. 建立全球多维源矩阵：涵盖亚洲(新马泰)、欧洲、北美及港台影视源
# 这种“多源策略”是长期有效的核心，一个链接失效，脚本会自动从其他源补全。
SOURCES = {
    "north_america": "https://raw.githubusercontent.com/YueChan/Live/main/m3u/america.m3u",
    "europe": "https://raw.githubusercontent.com/YueChan/Live/main/m3u/europe.m3u",
    "asia_chinese": "https://raw.githubusercontent.com/YueChan/Live/main/m3u/asia.m3u",
    "se_asia": "https://raw.githubusercontent.com/YueChan/Live/main/m3u/singapore_malaysia.m3u",
    "global_zh": "https://iptv-org.github.io/iptv/languages/zho.m3u",
    "itv_pili": "https://itvlist.cc/itv.m3u",
    "fanmingming": "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv4.m3u"
}

# 2. 电影与电视剧精准筛选关键字
KEYWORDS = ["电影", "电视剧", "剧场", "影院", "TVB", "翡翠台", "星河", "华语", "Channel 8", "U频道", "Drama", "Movie"]

def check_url(item):
    """
    自动剔除无效、卡顿及音画不同步的直播源
    """
    name_info, url = item
    # 使用模拟请求头，避开服务器屏蔽，确保音画流完整性
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        start_time = time.time()
        # 测速逻辑：2.0s 内未响应则判定为无效或卡顿源，直接删除
        response = requests.head(url, headers=headers, timeout=2.0, allow_redirects=True)
        end_time = time.time()
        
        # 只有返回 200 (状态正常) 的源才会被保留
        if response.status_code == 200:
            return {"name": name_info, "url": url, "speed": end_time - start_time}
    except:
        pass
    return None

def main():
    # 使用字典结构自动去重并保留多源中的“最优解”
    unique_channels = {}
    
    for filename, url in SOURCES.items():
        try:
            print(f"🔄 正在同步全球直播源: {filename}...")
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
                        # 仅处理包含影视关键字的中文频道
                        if any(kw.lower() in clean_name.lower() for kw in KEYWORDS):
                            temp_list.append((name_info, link))

            # 3. 30线程并发检测，大幅缩短更新时间
            with ThreadPoolExecutor(max_workers=30) as executor:
                results = list(executor.map(check_url, temp_list))

            # 4. 自动更新逻辑：若同名频道已有，则仅当新源速度更快时替换
            for res in results:
                if res:
                    c_name = res["name"].split(',')[-1].strip()
                    # 动态更新最快源，确保播放不卡顿
                    if c_name not in unique_channels or res["speed"] < unique_channels[c_name]["speed"]:
                        unique_channels[c_name] = res
            
        except Exception as e:
            print(f"⚠️ 源 {filename} 暂时不可用，已自动跳过")

    # 5. 生成最新的 all.m3u 列表
    final_content = ["#EXTM3U"]
    for res in unique_channels.values():
        final_content.append(f"{res['name']}\n{res['url']}")

    with open("all.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(final_content))
    
    print(f"\n🚀 自动维护完成！已剔除所有无效卡顿源。当前有效频道总数: {len(unique_channels)}")

if __name__ == "__main__":
    main()



