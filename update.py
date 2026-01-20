import requests

# 定义你的源
SOURCES = {
    "live.m3u": "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv4.m3u",
    "movie.m3u": "https://raw.githubusercontent.com/mizhenye/iptv/main/m3u/movie.m3u"
}

def main():
    all_content = ["#EXTM3U"] # 准备聚合文件的开头
    
    for filename, url in SOURCES.items():
        try:
            print(f"正在抓取: {filename}")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            
            # 过滤内容并添加到聚合列表
            lines = [line.strip() for line in r.text.split('\n') if '[' not in line and "#EXTM3U" not in line]
            
            # 保存单个文件
            with open(filename, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n" + "\n".join(lines))
            
            # 累加到聚合内容
            all_content.extend(lines)
            print(f"✅ {filename} 成功")
        except Exception as e:
            print(f"❌ {filename} 失败: {e}")

    # 最后生成一个包含所有频道的文件
    with open("all.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(all_content))
    print("✅ 聚合文件 all.m3u 已生成")

if __name__ == "__main__":
    main()

