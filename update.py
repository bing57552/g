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
        except Exception as e:
            logger.warning(f"源失效：{url[:50]} | 原因：{str(e)[:30]}")
            return 0.0, False

    def normalize_channel_name(self, name: str) -> str:
        if not name:
            return ''
        # 彻底清除所有源标识和冗余信息
        name = re.sub(r'_主源\d+|_备用源\d+|\(.*?\)|【.*?】', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^0-9A-Za-z一-鿿\s-]', '', name)
        return re.sub(r'\s+', ' ', name.strip()).strip()

    def process_sources(self, m3u_content: str) -> str:
        lines = m3u_content.strip().splitlines()
        streams = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF'):
                info = self.extract_channel_info(line)
                if info and info['raw_name'] and info['priority'] > 0:
                    i += 1
                    if i < len(lines):
                        url = lines[i].strip()
                        if url and 'http' in url:
                            norm_name = self.normalize_channel_name(info['raw_name'])
                            streams.append({
                                'norm_name': norm_name,
                                'tvg_id': f"tvg_{norm_name.replace(' ', '_')}",  # 生成唯一tvg-id
                                'group': info['group'],
                                'url': url,
                                'quality': info['quality'],
                                'priority': info['priority']
                            })
            i += 1

        if not streams:
            logger.error("未解析到有效直播源！")
            return '#EXTM3U\n# 无有效直播源'

        # 按标准化频道名和tvg-id分组
        channel_groups = {}
        for stream in streams:
            key = (stream['tvg_id'], stream['norm_name'])
            if key not in channel_groups:
                channel_groups[key] = []
            channel_groups[key].append(stream)

        result_lines = ['#EXTM3U x-tvg-url=""']
        for (tvg_id, norm_name), sources in channel_groups.items():
            # 测速并排序
            for source in sources:
                speed_score, available = self.test_stream_quality(source['url'])
                source['speed_score'] = speed_score
                source['available'] = available
                source['total_score'] = source['priority'] * 10 + source['speed_score'] * 2 + (10 if available else 0)
            available_sources = sorted([s for s in sources if s['available']], key=lambda x: x['total_score'], reverse=True)
            if available_sources:
                # 核心：所有源使用相同tvg-id和频道名
                for source in available_sources:
                    extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{norm_name}" group-title="{source["group"]}" quality="{source["quality"]}",{norm_name}'
                    result_lines.extend([extinf, source['url']])
                logger.info(f"✅ 频道 {norm_name} 已添加 {len(available_sources)} 个可用源")

        return '\n'.join(result_lines)

def main():
    processor = IPTVProcessor()
    m3u_url = os.getenv('M3U_SOURCE_URL')
    if not m3u_url:
        logger.error("❌ 未配置M3U_SOURCE_URL环境变量！")
        return
    try:
        response = requests.get(m3u_url, timeout=15, allow_redirects=True, verify=False, headers={'User-Agent': 'Mozilla/5.0 (GitHub Actions/IPTV)'})
        response.raise_for_status()
        m3u_content = response.text
    except Exception as e:
        logger.error(f"❌ 拉取M3U源失败：{str(e)}")
        return
    try:
        result_m3u = processor.process_sources(m3u_content)
    except Exception as e:
        logger.error(f"❌ 处理M3U源失败：{str(e)}", exc_info=True)
        return
    try:
        with open('output_multi_source_merged.m3u', 'w', encoding='utf-8') as f:
            f.write(result_m3u)
        logger.info("✅ 合并多源频道列表已保存到 output_multi_source_merged.m3u")
    except Exception as e:
        logger.error(f"❌ 保存文件失败：{str(e)}")

if __name__ == "__main__":
    main()
