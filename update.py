import requests
import re
import time
from urllib.parse import urlparse
from typing import List, Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IPTVProcessor:
    def __init__(self):
        self.quality_priority = {
            '4k': 4, '4K': 4, '2160p': 4,
            '1080p': 3, '1080P': 3, 'fhd': 3,
            '720p': 2, '720P': 2, 'hd': 2,
            '标清': 1, 'sd': 1, '480p': 1, '360p': 1
        }
        
    def extract_channel_info(self, m3u_line: str) -> Optional[Dict]:
        if not m3u_line.startswith('#EXTINF'):
            return None
            
        channel_name = None
        group_title = None
        quality = '标清'
        
        name_match = re.search(r',([^,]+)$', m3u_line)
        if name_match:
            channel_name = name_match.group(1).strip()
            
        group_match = re.search(r'group-title="([^"]*)"', m3u_line, re.IGNORECASE)
        if group_match:
            group_title = group_match.group(1).strip()
            
        for q in self.quality_priority.keys():
            if q.lower() in channel_name.lower() or q.lower() in m3u_line.lower():
                quality = q
                break
                
        return {
            'name': channel_name,
            'group': group_title,
            'quality': quality,
            'priority': self.quality_priority.get(quality.lower(), 1)
        }
    
    def test_stream_quality(self, url: str, timeout: int = 10) -> Tuple[float, bool]:
        try:
            start_time = time.time()
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            
            if response.status_code == 200:
                speed_score = 1.0 / (time.time() - start_time + 0.1)
                content_type = response.headers.get('content-type', '').lower()
                
                if 'm3u8' in content_type or url.endswith('.m3u8'):
                    speed_score *= 1.2
                elif 'video' in content_type or url.endswith('.ts'):
                    speed_score *= 1.1
                    
                return speed_score, True
            return 0.0, False
        except:
            return 0.0, False
    
    def normalize_channel_name(self, name: str) -> str:
        name = re.sub(r'[4-9]K|1080P?|720P?|标清|SD|HD|超清|高清|d+p', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^0-9A-Za-z一-鿿s-]', '', name)  # ✅ 修复正则
        name = re.sub(r's+', ' ', name.strip())
        return name.strip()
    
    def process_sources(self, m3u_content: str, max_workers: int = 10) -> str:
        lines = m3u_content.strip().split('
')  # ✅ 修复 split
        streams = []
        i = 0
        
        logger.info("开始解析M3U源...")
        
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('#EXTINF'):
                info = self.extract_channel_info(line)
                if not info or not info.get('name'):
                    i += 1
                    continue
                    
                i += 1
                if i >= len(lines):
                    break
                    
                url = lines[i].strip()
                if url and not url.startswith('#'):
                    streams.append({
                        'name': info['name'],
                        'group': info['group'] or '',
                        'url': url,
                        'quality': info['quality'],
                        'priority': info['priority'],
                        'normalized_name': self.normalize_channel_name(info['name'])
                    })
            i += 1
            
        logger.info(f"发现 {len(streams)} 个直播源")
        
        channel_groups = {}
        for stream in streams:
            norm_name = stream['normalized_name']
            if norm_name not in channel_groups:
                channel_groups[norm_name] = []
            channel_groups[norm_name].append(stream)
            
        logger.info(f"分组完成，共 {len(channel_groups)} 个频道")
        
        result_lines = ['#EXTM3U', '#EXT-X-VERSION:3']
        
        for norm_name, sources in channel_groups.items():
            logger.info(f"处理频道: {norm_name} ({len(sources)}个源)")
            
            for source in sources:
                speed_score, available = self.test_stream_quality(source['url'])
                sour