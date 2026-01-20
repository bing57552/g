import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor

# 1. 核心频道库：确保涵盖所有目标
KEYWORDS = [
    "CatchPlay", "CHC", "动作", "家庭影院", "影迷焦点", 
    "Astro", "华丽", "欢喜", "Pop", "TVB", "翡翠", 
    "星河", "无线", "myTV", "SUPER", "美亚", "八大", 
    "GTV", "高清", "超清", "1080P", "4K", "蓝光"
]


# 2. 稳定性检测：过滤掉无效、黑屏或卡顿的源
def check_url(item):
    name_info, url = item
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'}
    try:
        start_time = time.time()
        # 增加超时到 10s 以防优质海外源因响应慢被误删
        with requests.get(url, headers=headers, timeout=10.0, stream=True) as r:
            if r.status_code == 200:
                # 测速：读取一小块数据确认是否流畅
                chunk = next(r.iter_content(chunk_size=128*1024))
                speed = len(chunk) / 1024 / (time.time() - start_time)
                if speed > 300: # 确保至少 300KB/s 保证高清不卡
                    return {"name": name_info, "url": url}
    except:
        pass
    return None

# 3. 抓取与多线路生成逻辑
def main():
    # 备用源列表：一个失效会自动从下一个抓取
    sources = [
        "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",
        "https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u",
        "https://raw.githubusercontent.com/billy21/TVlist/master/view.m3u"
    ]
    
    temp_list = []
    for s_url in sources:
        try:
            r = requests.get(s_url, timeout=15)
            # 解析逻辑...
            # (此处根据关键字过滤并存入 temp_list)
        except:
            continue

    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(check_url, temp_list))

    # 4. 实现“多线路”而不“覆盖”
    final_output = ["#EXTM3U"]
    name_counts = {}
    
    valid_results = [res for res in results if res]
    
    # 【核心保护锁】：如果有效频道少于 5 个，极有可能是网络故障，禁止更新文件
    if len(valid_results) < 5:
        print("❌ 错误：有效频道太少，本次不更新文件，防止出现‘没有节目’的情况。")
        return

    for res in valid_results:
        raw_name = res["name"].split(',')[-1].strip()
        name_counts[raw_name] = name_counts.get(raw_name, 0) + 1
        
        # 自动编号：线路 1, 线路 2...
        suffix = f" (线路{name_counts[raw_name]})" if name_counts[raw_name] > 1 else ""
        display_name = f"{raw_name}{suffix}"
        final_output.append(f"#EXTINF:-1, {display_name}\n{res['url']}")

    with open("all.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(final_output))
    print(f"✅ 更新完成，共生成 {len(valid_results)} 条线路。")




