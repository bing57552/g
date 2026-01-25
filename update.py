import os
import requests
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from urllib.parse import urlparse

# 配置：你的远程直播源URL（直接替换成你的实际URL）
REMOTE_M3U_URL = "https://你的域名.com/demo.m3u"  # ← 这里填你的源

def get_channel_logic(name, url):
    """频道分类逻辑"""
    n = str(name).upper().replace(" ", "")
    
    # 电影频道（绝对保留）
    premium_movie = [
        "ASTRO", "CHC", "CATCHPLAY", "POPC", "美亚", "美亞", "DISNEY", "NETFLIX",
        "MOVIE", "电影", "電影", "影视", "影視", "CELESTIAL", "天映", "星卫", 
        "龍祥", "龙祥", "東森電影", "緯來電影", "纬来电影"
    ]
    if any(brand in n for brand in premium_movie):
        return "电影频道", False

    # 国语剧集频道
    mandarin_drama = ["电视剧", "戲劇", "戏剧", "劇場", "华剧", "華劇", "偶像剧", "DRAMA", "雙星", "全佳"]
    mandarin_tag = ["华语", "華語", "国语", "國語", "普通话", "MANDARIN", "CHINESE"]
    if any(k in n for k in mandarin_drama) and any(t in n for t in mandarin_tag):
        return "国语剧集频道", False

    # 港台频道
    if any(brand in n for brand in ["TVB", "MYTV", "GTV", "SUPER", "TW", "HK", "纬来", "东森"]):
        return "港台频道", False

    # 购物黑名单
    blacklist = ["QVC", "HSN", "JEWELRY", "JTV", "SHOPHQ", "EVINE", "GEM", "TSC", "TJC", "MOMO", "购物", "特卖", "商城"]
    if any(key in n for key in blacklist):
        return "垃圾购物台", True

    return "综合频道", False

def get_quality_priority(url):
    """清晰度优先级"""
    u = str(url).lower()
    if any(x in u for x in ['4k', 'uhd', '2160']):
        return 4, "[4K]"
    elif any(x in u for x in ['1080', 'fhd']):
        return 3, "[1080P]"
    elif any(x in u for x in ['720', 'hd']):
        return 2, "[高清]"
    else:
        return 1, "[标清]"

def check_stream_valid(url):
    """快速检测直播源（3秒超时）"""
    try:
        response = requests.head(url, timeout=3, allow_redirects=True)
        return response.status_code in [200, 206]
    except:
        try:
            response = requests.get(url, timeout=3, stream=True)
            return response.status_code in [200, 206]
        except:
            return False

def fetch_remote_playlist(url):
    """从远程URL拉取m3u播放列表"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ 远程源拉取失败: {e}")
        return None

def parse_m3u_content(content):
    """解析m3u内容，提取频道名和URL"""
    channels = defaultdict(list)
    lines = content.split('
')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 找到 #EXTINF 行
        if line.startswith('#EXTINF:'):
            try:
                # 提取频道名
                name_start = line.find(',') + 1
                name = line[name_start:].strip()
                
                # 找对应的URL（下一行或多行后）
                j = i + 1
                while j < len(lines):
                    url_line = lines[j].strip()
                    if url_line.startswith('http') and ',' not in url_line:
                        channels[name].append({
                            'url': url_line,
                            'line_num': i
                        })
                        break
                    j += 1
                
            except:
                pass
        
        i += 1
    
    return channels

def main():
    print("🚀 开始自动更新IPTV...")
    
    # 1. 从远程URL拉取直播源
    print(f"📡 拉取远程源: {REMOTE_M3U_URL}")
    content = fetch_remote_playlist(REMOTE_M3U_URL)
    if not content:
        print("❌ 拉取失败，退出")
        return
    
    # 2. 解析频道和URL
    print("📋 解析m3u播放列表...")
    channels = parse_m3u_content(content)
    print(f"✅ 发现 {len(channels)} 个频道")
    
    # 3. 检测直播源有效性
    print("🔍 并行检测直播源...")
    valid_streams = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(check_stream_valid, source['url']) for sources in channels.values() for source in sources]
        for future in as_completed(futures, timeout=90):
            try:
                valid_streams[future._args[0]] = future.result()
            except:
                pass
    
    print(f"✅ 有效源: {sum(valid_streams.values())} / {len(valid_streams)}")
    
    # 4. 生成优化后的m3u
    all_res = []
    clean_res = []
    
    for channel_name, sources in channels.items():
        # 分类
        group, is_shop = get_channel_logic(channel_name, sources[0]['url'] if sources else '')
        
        # 筛选有效源
        valid_sources = []
        for source in sources:
            if valid_streams.get(source['url'], False):
                priority, quality_tag = get_quality_priority(source['url'])
                valid_sources.append({
                    **source,
                    'priority': priority,
                    'quality_tag': quality_tag,
                    'group': group,
                    'is_shop': is_shop
                })
        
        if not valid_sources:
            print(f"⚠️  {channel_name} 所有源无效")
            continue
        
        # 按清晰度排序，取前3个
        valid_sources.sort(key=lambda x: x['priority'], reverse=True)
        top_sources = valid_sources[:3]
        
        # 生成m3u条目
        for source in top_sources:
            display_name = f"{channel_name} {source['quality_tag']}"
            entry = f'#EXTINF:-1 group-title="{source["group"]}",{display_name}
{source["url"]}
'
            
            all_res.append(entry)
            if not source['is_shop']:
                clean_res.append(entry)
    
    # 5. 输出文件
    with open("all.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U
" + "".join(all_res))
    
    with open("no-shopping.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U
" + "".join(clean_res))
    
    print(f"🎉 更新完成!")
    print(f"   📺 all.m3u: {len(all_res)} 个源")
    print(f"   🛒 no-shopping.m3u: {len(clean_res)} 个源")

if __name__ == "__main__":
    main()