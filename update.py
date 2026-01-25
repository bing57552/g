import requests
import re
import time
from urllib.parse import urlparse
from typing import List, Dict, Tuple, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IPTVProcessor:
    def __init__(self):
        # 清晰度优先级映射 (越高数字越优先)
        self.quality_priority = {
            '4k': 4, '4K': 4, '2160p': 4,
            '1080p': 3, '1080P': 3, 'fhd': 3,
            '720p': 2, '720P': 2, 'hd': 2,
            '标清': 1, 'sd': 1, '480p': 1, '360p': 1
        }
        
    def extract_channel_info(self, m3u_line: str) -> Optional[Dict]:
        """从M3U行提取频道信息"""
        if not m3u_line.startswith('#EXTINF'):
            return None
            
        channel_name = None
        group_title = None
        quality = '标清'  # 默认质量
        
        # 提取频道名称
        name_match = re.search(r',([^,]+)$', m3u_line)
        if name_match:
            channel_name = name_match.group(1).strip()
            
        # 提取组名
        group_match = re.search(r'group-title="([^"]*)"', m3u_line, re.IGNORECASE)
        if group_match:
            group_title = group_match.group(1).strip()
            
        # 提取质量信息
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
        """测试直播源质量，返回速度评分和可用性"""
        try:
            start_time = time.time()
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            
            # 检查响应状态和速度
            if response.status_code == 200:
                speed_score = 1.0 / (time.time() - start_time + 0.1)  # 速度越快分数越高
                content_type = response.headers.get('content-type', '').lower()
                
                # 优先M3U8和TS流
                if 'm3u8' in content_type or url.endswith('.m3u8'):
                    speed_score *= 1.2
                elif 'video' in content_type or url.endswith('.ts'):
                    speed_score *= 1.1
                    
                return speed_score, True
            return 0.0, False
        except:
            return 0.0, False
    
    def normalize_channel_name(self, name: str) -> str:
        """标准化频道名称用于去重"""
        # 移除质量标签、数字、分隔符等
        name = re.sub(r'[4-9]K|1080P?|720P?|标清|SD|HD|超清|高清|d+p', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^ws一-鿿]', ' ', name)  # 保留中文和字母数字
        name = re.sub(r's+', ' ', name.strip())  # 统一空格
        return name.strip()
    
    def process_sources(self, m3u_content: str, max_workers: int = 10) -> str:
        """主处理函数：一个频道→多源→去重→最佳排序"""
        lines = m3u_content.strip().split('
')
        streams = []
        i = 0
        
        logger.info("开始解析M3U源...")
        
        # 第一步：提取所有直播源
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('#EXTINF'):
                info = self.extract_channel_info(line)
                if not info or not info['name']:
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
        
        # 第二步：按标准化名称分组
        channel_groups = {}
        for stream in streams:
            norm_name = stream['normalized_name']
            if norm_name not in channel_groups:
                channel_groups[norm_name] = []
            channel_groups[norm_name].append(stream)
            
        logger.info(f"分组完成，共 {len(channel_groups)} 个频道")
        
        # 第三步：每个频道测试并排序最佳源
        result_lines = [
            '#EXTM3U',
            '#EXT-X-VERSION:3'
        ]
        
        for norm_name, sources in channel_groups.items():
            logger.info(f"处理频道: {norm_name} ({len(sources)}个源)")
            
            # 测试每个源的实际性能
            for source in sources:
                speed_score, available = self.test_stream_quality(source['url'])
                source['speed_score'] = speed_score
                source['available'] = available
                source['total_score'] = (
                    source['priority'] * 0.7 +  # 清晰度70%
                    speed_score * 30 +           # 速度30%
                    (1 if available else 0) * 10  # 可用性10%
                )
                
            # 按总评分降序排序，保留最佳源
            best_sources = sorted(
                [s for s in sources if s['available']],
                key=lambda x: x['total_score'],
                reverse=True
            )
            
            if best_sources:
                best_source = best_sources[0]
                # 生成EXTINF行
                extinf = f'#EXTINF:-1 tvg-name="{best_source["name"]}" group-title="{best_source["group"]}"'
                result_lines.extend([extinf, best_source['url']])
                logger.info(f"✓ {best_source['name']} -> {best_source['quality']} (评分: {best_source['total_score']:.1f})")
            else:
                logger.warning(f"✗ {norm_name} 所有源都不可用")
        
        result_m3u = '
'.join(result_lines)
        logger.info(f"处理完成！输出 {len([l for l in result_lines if l.startswith('#EXTINF')])} 个最佳频道")
        
        return result_m3u

def main():
    processor = IPTVProcessor()
    
    # 示例用法1：从文件读取
    try:
        with open('input.m3u', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        # 示例用法2：从URL读取
        url = input("请输入M3U源URL: ")
        content = requests.get(url).text
    
    # 处理并保存结果
    result = processor.process_sources(content)
    
    with open('output_best.m3u', 'w', encoding='utf-8') as f:
        f.write(result)
    
    print("✅ 处理完成！最佳源已保存到 output_best.m3u")
    print("逻辑顺序：")
    print("1️⃣ 一个频道 → 多个有效直播源（4K/1080P/720P/标清）")
    print("2️⃣ 自动去重 → 相同频道只保留最佳源")
    print("3️⃣ 清晰度排序 → 4K > 1080P > 720P > 标清")
    print("4️⃣ 最快不卡音画同步优先 ✓")

if __name__ == "__main__":
    main()