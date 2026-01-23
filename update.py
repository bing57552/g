import os

def get_channel_logic(name, url):
    """
    零失误逻辑：
    1. 核心白名单：绝对保护，命中后直接跳过黑名单检测。
    2. 全球黑名单：涵盖所有 QVC, HSN, Momo, 以及各国购物台。
    """
    n = str(name).upper().replace(" ", "")
    u = str(url).lower()

    # ==========================================
    # 1. 【绝对白名单】—— 只要名字包含这些，绝对不拦截
    # ==========================================
    premium_brands = [
        "ASTRO", "CHC", "CATCHPLAY", "POPC", "MYTV", "TVB", "GTV", 
        "美亚", "DISNEY", "NETFLIX", "MOVIE", "电影", "影视",
        "TW", "HK", "［TW］", "[HK]", "SUPER", "纬来", "龙祥", "东森"
    ]

    if any(brand in n for brand in premium_brands):
        if any(x in n for x in ["TVB", "MYTV", "GTV", "SUPER", "TW", "HK"]):
            return "港台频道", False
        return "电影频道", False

    # ==========================================
    # 2. 【全球购物黑名单】—— 命中即刻过滤
    # ==========================================
    shopping_blacklist = [
        # 欧美大牌
        "QVC", "HSN", "JEWELRY", "JTV", "SHOPHQ", "EVINE", "GEMSHOPPING", "LIQUIDATION",
        "AUCTIONNETWORK", "TSC", "THESHOPPINGCHANNEL", "TJC", "CREATEANDCRAFT", "GEMS",
        "JMLDIRECT", "JUWELO", "1-2-3TV", "M6BOUTIQUE", "TELESHOPPING",
        # 中国及港澳台
        "中视购物", "央广购物", "环球购物", "聚鲨环球", "家有购物", "快乐购物", "芒果购物",
        "好享购物", "时尚购物", "家家购物", "优购物", "风尚购物", "东方购物", "好易购",
        "南方购物", "宜和购物", "星空购物", "乐思购", "乐家购物", "MOMO购物", "电视广播购物",
        "澳广视购物", 
        # 日韩及东南亚
        "乐天TV", "富士TV购物", "TBS购物", "日本雅虎购物", "CJOSHOPPING", "GSSHOP", 
        "HYUNDAIHOMESHOPPING", "COUPANGTV", "SHOPTV", "TRUESHOPPING", "STARHUBSHOPPING",
        "MNCSHOPPING", "HOMESHOP18", "NAAPTOL", 
        # 澳洲、新西兰及其他
        "TVSN", "ASPIRETV", "SPREETV", "ISHOPTV", "YESSHOP", "SHOPTVBRASIL", 
        "TELEVISASHOPPING", "SHOPPINGTV", "MERCADOLIBRE", "DUBAISHOPPING", "MBCSHOPPING",
        "JUMIATV", "购物台", "特卖", "商城"
    ]

    # 特征识别：URL中包含购物关键字且不在白名单内的
    url_shopping_features = ["shopping", "liveshopping", "mall", "buy-tv", "tvshop"]

    if any(key in n for key in shopping_blacklist) or any(feat in u for feat in url_shopping_features):
        return "垃圾购物台", True

    return "综合频道", False

def main():
    # 数据源：请确保你的源文件名为 demo.txt
    input_file = "demo.txt" 
    output_all = "all.m3u"
    output_clean = "no-shopping.m3u"

    if not os.path.exists(input_file):
        print(f"❌ 找不到源文件 {input_file}")
        return

    all_m3u = []
    clean_m3u = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if "," in line and "://" in line:
                try:
                    name, url = line.split(",", 1)
                    group, should_filter = get_channel_logic(name, url)
                    entry = f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n'
                    all_m3u.append(entry)
                    if not should_filter:
                        clean_m3u.append(entry)
                except:
                    continue

    with open(output_all, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n" + "".join(all_m3u))
    
    with open(output_clean, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n" + "".join(clean_m3u))

    print(f"✅ 处理成功：全球 {len(shopping_blacklist)} 类购物频道已被拦截。")

if __name__ == "__main__":
    main()
