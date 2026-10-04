"""
微信公众号文章类型检测器 - 增强版

文章类型定义：
0 = 图文（普通文章，包含文字和图片）
5 = 视频（包含视频内容）
7 = 音频（包含音频内容）
10 = 贴图（主要是图片，文字很少）
11 = 分享（分享链接类型）

使用方法：
1. 直接检测URL: detector.detect_type(url)
2. 批量检测: detector.batch_detect(urls)
3. 从HTML内容检测: detector.detect_type_from_html(html_content)

注意事项：
- 微信公众号文章可能需要JavaScript渲染才能获取完整内容
- 建议使用Selenium或Playwright等工具获取完整HTML
- 或者从微信后台API获取文章信息
"""

import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json


class ArticleTypeDetector:
    """微信公众号文章类型检测器"""
    
    # 文章类型常量
    TYPE_IMAGE_TEXT = 0      # 图文
    TYPE_VIDEO = 5           # 视频
    TYPE_AUDIO = 7           # 音频
    TYPE_STICKER = 10        # 贴图
    TYPE_SHARE = 11          # 分享
    
    TYPE_NAMES = {
        0: '图文',
        5: '视频',
        7: '音频',
        10: '贴图',
        11: '分享'
    }
    
    def __init__(self, headers=None, timeout=15):
        """
        初始化检测器
        
        Args:
            headers: 自定义请求头
            timeout: 请求超时时间
        """
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.timeout = timeout
    
    def detect_type(self, url):
        """
        检测文章类型（从URL）
        
        Args:
            url: 微信公众号文章链接
            
        Returns:
            dict: 包含类型信息和特征的字典
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            html = response.text
            
            return self.detect_type_from_html(html, url)
            
        except requests.exceptions.RequestException as e:
            return {
                'url': url,
                'error': f'网络请求失败: {str(e)}',
                'success': False
            }
        except Exception as e:
            return {
                'url': url,
                'error': f'分析失败: {str(e)}',
                'success': False
            }
    
    def detect_type_from_html(self, html, url=''):
        """
        从HTML内容检测文章类型
        
        Args:
            html: HTML内容
            url: 文章URL（可选）
            
        Returns:
            dict: 包含类型信息和特征的字典
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取文章信息
            title = self._extract_title(html, soup)
            content_info = self._analyze_content(html, soup)
            
            # 判断文章类型
            article_type = self._determine_type(content_info)
            
            return {
                'url': url,
                'title': title,
                'type': article_type,
                'type_name': self.TYPE_NAMES.get(article_type, '未知'),
                'features': content_info,
                'success': True
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': f'分析失败: {str(e)}',
                'success': False
            }
    
    def _extract_title(self, html, soup):
        """提取文章标题"""
        # 方法1: 从JavaScript变量中提取
        title_match = re.search(r'var msg_title = "(.*?)";', html)
        if title_match:
            return title_match.group(1)
        
        # 方法2: 从meta标签提取
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title['content']
        
        # 方法3: 从title标签提取
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # 方法4: 从h1标签提取
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
        
        return '未知标题'
    
    def _analyze_content(self, html, soup):
        """分析文章内容特征"""
        features = {
            'has_video': False,
            'has_audio': False,
            'has_images': False,
            'is_share': False,
            'image_count': 0,
            'video_count': 0,
            'audio_count': 0,
            'text_length': 0,
            'paragraph_count': 0
        }
        
        # 检测视频
        features['has_video'] = self._detect_video(html, soup, features)
        
        # 检测音频
        features['has_audio'] = self._detect_audio(html, soup, features)
        
        # 检测图片
        features['has_images'] = self._detect_images(html, soup, features)
        
        # 检测分享
        features['is_share'] = self._detect_share(html, soup)
        
        # 统计文本内容
        self._analyze_text_content(soup, features)
        
        return features
    
    def _detect_video(self, html, soup, features):
        """检测视频内容"""
        # 检查iframe视频
        video_iframes = soup.find_all('iframe', class_='video_iframe')
        features['video_count'] = len(video_iframes)
        
        # 检查video标签
        video_tags = soup.find_all('video')
        features['video_count'] += len(video_tags)
        
        # 检查mpvideo标签
        mpvideo_tags = soup.find_all('mpvideo')
        features['video_count'] += len(mpvideo_tags)
        
        # 检查data-type="video"
        video_data = soup.find_all(attrs={'data-type': 'video'})
        features['video_count'] += len(video_data)
        
        # 检查HTML中的视频特征字符串
        video_patterns = [
            r'video_iframe',
            r'mpvideo',
            r'data-type="video"',
            r'mpvid',
            r'<video[^>]*>',
            r'player\.video',
            r'type:\s*[\'"]video[\'"]'
        ]
        
        for pattern in video_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                features['video_count'] += len(matches)
        
        return features['video_count'] > 0
    
    def _detect_audio(self, html, soup, features):
        """检测音频内容"""
        # 检查mpvoice标签
        audio_tags = soup.find_all('mpvoice')
        features['audio_count'] = len(audio_tags)
        
        # 检查audio标签
        audio_html_tags = soup.find_all('audio')
        features['audio_count'] += len(audio_html_tags)
        
        # 检查data-type="audio"
        audio_data = soup.find_all(attrs={'data-type': 'audio'})
        features['audio_count'] += len(audio_data)
        
        # 检查HTML中的音频特征字符串
        audio_patterns = [
            r'mpvoice',
            r'data-type="audio"',
            r'voice_encode_fileid',
            r'<audio[^>]*>',
            r'type:\s*[\'"]audio[\'"]'
        ]
        
        for pattern in audio_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                features['audio_count'] += len(matches)
        
        return features['audio_count'] > 0
    
    def _detect_images(self, html, soup, features):
        """检测图片内容"""
        # 检查rich_pages类图片
        rich_images = soup.find_all('img', class_='rich_pages')
        features['image_count'] = len(rich_images)
        
        # 检查data-type为图片的img标签
        for data_type in ['jpeg', 'png', 'gif', 'webp']:
            img_tags = soup.find_all('img', attrs={'data-type': data_type})
            features['image_count'] += len(img_tags)
        
        # 检查所有img标签（排除表情图标等）
        all_images = soup.find_all('img')
        for img in all_images:
            src = img.get('src', '')
            data_src = img.get('data-src', '')
            
            # 微信图片域名
            if any(domain in src or domain in data_src for domain in ['mmbiz.qpic.cn', 'mmbiz.qlogo.cn']):
                features['image_count'] += 1
        
        # 检查HTML中的图片特征字符串
        image_patterns = [
            r'rich_pages',
            r'data-type="jpeg"',
            r'data-type="png"',
            r'data-type="gif"',
            r'mmbiz\.qpic\.cn',
            r'mmbiz\.qlogo\.cn'
        ]
        
        for pattern in image_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                features['image_count'] += len(matches)
        
        return features['image_count'] > 0
    
    def _detect_share(self, html, soup):
        """检测分享类型"""
        # 检查data-type="share"
        if soup.find(attrs={'data-type': 'share'}):
            return True
        
        # 检查分享链接特征
        share_patterns = [
            r'data-type="share"',
            r'share_card',
            r'share_link',
            r'share_title'
        ]
        
        for pattern in share_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                return True
        
        return False
    
    def _analyze_text_content(self, soup, features):
        """分析文本内容"""
        # 获取文章内容区域
        content_area = soup.find('div', class_='rich_media_content')
        if not content_area:
            content_area = soup.find('div', id='js_content')
        if not content_area:
            content_area = soup
        
        # 统计段落
        paragraphs = content_area.find_all('p')
        features['paragraph_count'] = len(paragraphs)
        
        # 统计文本长度
        text = content_area.get_text()
        features['text_length'] = len(text.strip())
    
    def _determine_type(self, features):
        """根据特征确定文章类型"""
        # 优先级：视频 > 音频 > 分享 > 贴图 > 图文
        
        if features['has_video']:
            return self.TYPE_VIDEO
        
        if features['has_audio']:
            return self.TYPE_AUDIO
        
        if features['is_share']:
            return self.TYPE_SHARE
        
        # 判断是否为贴图（图片多，文字少）
        if features['has_images'] and features['image_count'] >= 3:
            # 如果图片数量多，且文字内容很少，认为是贴图
            if features['text_length'] < 200 or features['paragraph_count'] < 3:
                return self.TYPE_STICKER
        
        # 默认为图文
        return self.TYPE_IMAGE_TEXT
    
    def batch_detect(self, urls):
        """
        批量检测文章类型
        
        Args:
            urls: URL列表
            
        Returns:
            list: 检测结果列表
        """
        results = []
        for url in urls:
            result = self.detect_type(url)
            results.append(result)
        return results


def print_result(result, index=None):
    """格式化打印检测结果"""
    prefix = f"文章{index}: " if index else ""
    
    if result['success']:
        print(f"{prefix}{result['title'][:60]}")
        print(f"  类型: {result['type']} - {result['type_name']}")
        print(f"  特征:")
        print(f"    - 视频: {result['features']['has_video']} (数量: {result['features']['video_count']})")
        print(f"    - 音频: {result['features']['has_audio']} (数量: {result['features']['audio_count']})")
        print(f"    - 图片: {result['features']['has_images']} (数量: {result['features']['image_count']})")
        print(f"    - 分享: {result['features']['is_share']}")
        print(f"    - 文本长度: {result['features']['text_length']} 字符")
        print(f"    - 段落数: {result['features']['paragraph_count']}")
    else:
        print(f"{prefix}分析失败 - {result.get('error', '未知错误')}")


def main():
    """主函数 - 示例用法"""
    # 示例URL列表
    urls = [
        'https://mp.weixin.qq.com/s/jfhRhSD8CO4d6Op2ljuhVA',
        'https://mp.weixin.qq.com/s/cMB3xubsPlYRnS2gKKteIg',
        'https://mp.weixin.qq.com/s/dvL0lgjIAF7u_Vk36GKRTQ',
        'https://mp.weixin.qq.com/s/f7rLB4L9DGDOfkwCnbR67w',
        'https://mp.weixin.qq.com/s/4svk-UsVuyThdpwUJaYdRQ'
    ]
    
    detector = ArticleTypeDetector()
    
    print("=" * 80)
    print("微信公众号文章类型检测")
    print("=" * 80)
    print()
    
    for i, url in enumerate(urls, 1):
        print(f"正在分析文章 {i}/{len(urls)}...")
        result = detector.detect_type(url)
        print_result(result, i)
        print()
    
    print("=" * 80)
    print("检测完成")
    print("=" * 80)


if __name__ == '__main__':
    main()
