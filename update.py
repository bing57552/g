import requests
import re
import time
import os
import logging

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IPTVProcessor:
    def __init__(self):
        self.quality_priority = {
            '4k': 10, '4K': 10, '2160p': 10,
            '1080p': 8, '1080P': 8, 'fhd': 8,
            '720p': 1, '720P': 1, 'hd': 1,
            '标清': 0, 'sd': 0, '480p': 0, '360p': 0
        }

    def extract_channel_info(self, m3u_line: str):
        if not m3u_line.startswith('#EXTINF'):
            return None
        name_match = re.search(r',([^,]+)$', m3u_line)
        group_match = re.search(r'group-title="([^"]*)"', m3u_line, re.IGNORECASE)

        quality = '1080p'
        for q in self.quality_priority.keys():
            if q.lower() in m3u_line.lower():
                quality = q
                break

        return {
            'raw_name': name_match.group(1).strip() if name_match else None,
            'group': group_match.group(1).strip() if group_match else '综合频道',
            'quality': quality,
            'priority': self.quality_priority.get(quality.lower(), 0)
        } if name_match else None

    def test_stream_quality(self, url: str, timeout: int = 6):
        try:
            start_time = time.time()
            response = requests.head(
                url, timeout=timeout, allow_redirects=True, verify=False,
                headers={'User-Agent': 'Mozilla/5.0 (IPTV/Player)'}
            )
            if response.status_code == 200:
                delay = time.time() - start_time
                speed_score = 1.0 / (delay + 0.01)
                content_type = response.headers.get('content-type', '').lower()

                if 'm3u8' in content_type or url.endswith('.m3u8'):
                    speed_score *= 1.5
                elif 'video' in content_type or url.endswith('.ts'):
                    speed_score *= 1.2

                if delay > 3:
                    speed_score *= 0.3

                return round(speed_score, 2), True

            return 0.0, False
        except Exception:
            return 0.0, False

    def normalize_channel_name(self, name: str) -> str:
        if not name:
            return ''
        name = re.sub(r'_主源\d+|_备用源\d+|\(.*?\)|【.*?】', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^0-9A-Za-z一-鿿\s-]', '', name)
        return re.sub(r'\s+', ' ', name.strip())

    def process_sources(self, m3u_content: str) -> str:
        lines = m3u_content.strip().splitlines()
        streams = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF'):
                info = self.extract_channel_info(line)
                if info and info['raw_name'] and info['priority'] >= 0:
                    i += 1
                    if i < len(lines):
                        url = lines[i].strip()
                        if url.startswith('http'):
                            norm_name = self.normalize_channel_name(info['raw_name'])
                            streams.append({
                                'norm_name': norm_name,
                                'tvg_id': f"tvg_{norm_name.replace(' ', '_')}",
                                'group': info['group'],
                                'url': url,
                                'quality': info['quality'],
                                'priority': info['priority']
                            })
            i += 1

        if not streams:
            return '#EXTM3U\n# no valid streams'

        channel_groups = {}
        for s in streams:
            key = (s['tvg_id'], s['norm_name'])
            channel_groups.setdefault(key, []).append(s)

        result = ['#EXTM3U']
        for (tvg_id, name), sources in channel_groups.items():
            for s in sources:
                speed, ok = self.test_stream_quality(s['url'])
                s['available'] = ok
                s['score'] = s['priority'] * 10 + speed * 2 + (10 if ok else 0)

            good = sorted([s for s in sources if s['available']], key=lambda x: x['score'], reverse=True)

            for s in good:
                result.append(
                    f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{s["group"]}",{name}'
                )
                result.append(s['url'])

        return '\n'.join(result)


# ================== ✅ 新增：全仓库读取 ==================
def load_all_m3u_from_repo(root='.'):
    contents = []
    for r, _, files in os.walk(root):
        for f in files:
            if f.endswith('.m3u') and not f.startswith('ALL_'):
                path = os.path.join(r, f)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                        contents.append(fp.read())
                        logger.info(f'📥 读取 {path}')
                except Exception as e:
                    logger.warning(f'跳过 {path}: {e}')
    return '\n'.join(contents)
# =======================================================


def main():
    processor = IPTVProcessor()

    # ✅ 核心改动：不再使用远程 URL
    m3u_content = load_all_m3u_from_repo('.')

    if not m3u_content.strip():
        logger.error('❌ 未读取到任何 m3u 内容')
        return

    result = processor.process_sources(m3u_content)

    with open('ALL_IN_ONE.m3u', 'w', encoding='utf-8') as f:
        f.write(result)

    logger.info('✅ 全聚合 IPTV 已生成：ALL_IN_ONE.m3u')


if __name__ == '__main__':
    main()