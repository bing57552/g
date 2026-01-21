# update.py
import os
import re

OUT_FILE = "all.m3u"

# ===== 频道名统一 =====
def normalize_name(name: str) -> str:
    return (
        name.replace("HD", "")
            .replace("高清", "")
            .replace("标清", "")
            .replace("频道", "")
            .replace(" ", "")
            .strip()
    )

# ===== 购物 / 广告 过滤规则 =====
BLOCK_PATTERNS = [
    r"购物", r"购", r"Shopping", r"SHOP",
    r"广告", r"AD$", r"Promo",
    r"导购", r"特卖", r"优选",
    r"购物指南", r"电视购物"
]

def is_blocked(name: str) -> bool:
    for p in BLOCK_PATTERNS:
        if re.search(p, name, re.IGNORECASE):
            return True
    return False

channels = {}  # {频道名: set(url)}

# ===== 扫描所有 m3u =====
for root, _, files in os.walk("."):
    for file in files:
        if not file.endswith(".m3u"):
            continue
        if file == OUT_FILE:
            continue

        path = os.path.join(root, file)
        with open(path, encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()

        current = None
        for line in lines:
            line = line.strip()

            if line.startswith("#EXTINF"):
                name = line.split(",")[-1]
                name = normalize_name(name)

                # 🚫 过滤广告 / 购物
                if is_blocked(name):
                    current = None
                    continue

                current = name
                channels.setdefault(current, set())

            elif line.startswith("http") and current:
                channels[current].add(line)

# ===== 输出 all.m3u =====
with open(OUT_FILE, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")
    for name in sorted(channels):
        for url in sorted(channels[name]):
            out.write(f"#EXTINF:-1,{name}\n")
            out.write(f"{url}\n")

print(f"完成：保留 {len(channels)} 个频道（已去广告/购物）")