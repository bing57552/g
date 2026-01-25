import os

def get_channel_logic(name, url):
    """
    根据频道名决定分组，并返回 (分组名, 是否为购物台)
    name: 频道名
    url : 频道地址（目前未使用，预留扩展）
    """
    # 名字统一处理：大写 + 去空格
    n = str(name).upper().replace(" ", "")
    u = str(url).lower()  # 现在没用到，但先保留

    # ===== 1. 电影频道：任何命中以下关键字，都直接归到电影组 =====
    premium_movie = [
        "ASTRO", "CHC", "CATCHPLAY", "POPC",
        "美亚", "美亞",
        "DISNEY", "NETFLIX",
        "MOVIE", "电影", "電影", "影视", "影視",
        "CELESTIAL", "天映", "天映經典", "天映经典",
        "星卫", "星衛", "龍祥", "龙祥",
        "東森電影", "東森洋片", "东森电影", "东森洋片",
        "緯來電影", "纬来电影", "星衛電影", "星卫电影"
    ]
    if any(brand in n for brand in premium_movie):
        return "电影频道", False

    # ===== 2. 国语 / 华语剧集频道 =====
    # 条件：同时命中 “戏剧类关键词” + “华语/国语标签”
    mandarin_drama = [
        "电视剧", "電視劇",
        "戲劇", "戏剧",
        "劇場", "剧场",
        "華劇", "华剧",
        "偶像劇", "偶像剧",
        "DRAMA",
        "雙星", "双星",
        "全佳",
        "AOD",
        "華麗台", "华丽台"
    ]
    mandarin_tag = [
        "華語", "华语",
        "國語", "国语",
        "普通話", "普通话",
        "MANDARIN", "CHINESE"
    ]
    if any(k in n for k in mandarin_drama) and any(t in n for t in mandarin_tag):
        return "国语剧集频道", False

    # ===== 3. 港台频道：TVB / MYTV / 纬来 / 龙祥 / 东森等 =====
    if any(brand in n for brand in [
        "TVB", "MYTV", "GTV", "SUPER", "TW", "HK",
        "纬来", "緯來",
        "龙祥", "龍祥",
        "东森", "東森"
    ]):
        return "港台频道", False

    # ===== 4. 购物黑名单：命中则视为垃圾购物台，从精简列表中剔除 =====
    blacklist = [
        "QVC", "HSN", "JEWELRY", "JTV", "SHOPHQ", "EVINE",
        "GEM", "TSC", "TJC", "MOMO",
        "购物", "購物", "特卖", "特賣", "商城"
    ]
    if any(key in n for key in blacklist):
        return "垃圾购物台", True

    # ===== 5. 默认：综合频道 =====
    return "综合频道", False


def main():
    # 输入文件：每行格式为 频道名,URL
    input_file = "demo.txt"
    if not os.path.exists(input_file):
        return

    all_res = []
    clean_res = []  # 去购物后的干净列表

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            # 简单判断一下这一行是不是 “名字,链接” 格式
            if "," in line and "://" in line:
                try:
                    name, url = line.strip().split(",", 1)
                    group, is_shop = get_channel_logic(name, url)
                    entry = f'#EXTINF:-1 group-title="{group}",{name}
{url}
'

                    # 全部频道
                    all_res.append(entry)
                    # 去除购物台后的频道
                    if not is_shop:
                        clean_res.append(entry)
                except Exception:
                    # 任意解析错误直接跳过该行，避免脚本中断
                    continue

    # 输出包含所有频道的列表
    with open("all.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U
" + "".join(all_res))

    # 输出去购物后的干净列表
    with open("no-shopping.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U
" + "".join(clean_res))


if __name__ == "__main__":
    main()