import requests
import re
import time
import os
import logging
from collections import defaultdict

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IPTVProcessor:
    def __init__(self):
        self.quality_priority = {
            '4k': 10, '2160p': 10,
            '1080p': 8, 'fhd': 8,
            '720p': 4, 'hd': 4,
            'sd': 1
        }

    def normalize_name(self, name: str) -> str:
        if not name:
            return ''
        name = re.sub(r'\(.*?\)|【.*?】|_备用.*|_主源.*', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name.strip()

    def extract_info(self, extinf: str):
        name_match = re.search(r',(.+)$', extinf)
        group_match = re.search(r'group-title="([^"]*)"', extinf)
        quality = 'sd'
        for q in self.quality_priority:
            if q in extinf.lower():
                quality = q
                break
        return {
            "name": self.normalize_name(name_match.group(1)) if name_match else None,
            "group": group_match.group(1) if group_match else "未分类",
            "quality": quality,
            "priority": self.quality_priority.get(quality, 1)
        }

    def test_url(self, url: str, timeout=6):
        try:
            start = time.time()
            r = requests.head(
                url,
                timeout=timeout,
                allow_redirects=True,
                verify=False,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if r.status_code == 200:
                delay = time.time() - start
                score = max(0.1, 3 - delay)
                return True, round(score, 2)
        except:
            pass
        return False, 0.0

    def process(self, m3u: str) -> str:
        lines = m3u.splitlines()
        channels = defaultdict(list)

        i = 0
        while i < len(lines):
            if lines[i].startswith("#EXTINF"):
                info = self.extract_info(lines[i])
                if info and i + 1 < len(lines):
                    url = lines[i + 1].strip()
                    if url.startswith("http"):
                        channels[info["name"]].append({
                            "url": url,
                            "group": info["group"],
                            "priority": info["priority"]
                        })
                i += 2
            else:
                i += 1

        result = ["#EXTM3U"]

        for name, sources in channels.items():
            tested = []
            for s in sources:
                ok, speed = self.test_url(s["url"])
                if ok:
                    s["speed"] = speed
                    s["score"] = s["priority"] * 10 + speed
                    tested.append(s)

            if not tested:
                continue

            tested.sort(key=lambda x: x["score"], reverse=True)
            best = tested[0]

            # ✅ 只写一次 EXTINF
            result.append(
                f'#EXTINF:-1 tvg-name="{name}" group-title="{best["group"]}",{name}'
            )

            # ✅ 多个源只写 URL
            for s in tested:
                result.append(s["url"])

            logger.info(f"✅ {name} 合并 {len(tested)} 个源")

        return "\n".join(result)


def main():
    url = os.getenv("M3U_SOURCE_URL")
    if not url:
        logger.error("未设置 M3U_SOURCE_URL")
        return

    try:
        r = requests.get(url, timeout=15, verify=False)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"拉取源失败: {e}")
        return

    processor = IPTVProcessor()
    output = processor.process(r.text)

    with open("ALL_IN_ONE.m3u", "w", encoding="utf-8") as f:
        f.write(output)

    logger.info("🎉 ALL_IN_ONE.m3u 已生成")


if __name__ == "__main__":
    main()