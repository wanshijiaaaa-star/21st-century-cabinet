import requests
import re
from bs4 import BeautifulSoup

def analyze_article_type(url):
    """分析微信公众号文章类型"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 检查视频特征
        has_video = (
            'video_iframe' in html or 
            'mpvideo' in html or 
            'data-type="video"' in html or
            bool(soup.find('iframe', class_='video_iframe')) or
            bool(soup.find(attrs={'data-type': 'video'}))
        )
        
        # 检查音频特征
        has_audio = (
            'mpvoice' in html or 
            'data-type="audio"' in html or
            bool(soup.find('mpvoice')) or
            bool(soup.find(attrs={'data-type': 'audio'}))
        )
        
        # 检查图片特征
        has_images = (
            'rich_pages' in html or 
            'data-type="jpeg"' in html or 
            'data-type="png"' in html or
            bool(soup.find('img', class_='rich_pages')) or
            bool(soup.find('img', attrs={'data-type': ['jpeg', 'png']}))
        )
        
        # 检查分享特征
        is_share = (
            'data-type="share"' in html or
            bool(soup.find(attrs={'data-type': 'share'}))
        )
        
        # 检查贴图特征（主要是图片，没有文字内容）
        is_sticker = (
            has_images and 
            not has_video and 
            not has_audio and
            len(soup.find_all('p')) < 3  # 段落很少
        )
        
        # 获取标题
        title_match = re.search(r'var msg_title = "(.*?)";', html)
        title = title_match.group(1) if title_match else '未知标题'
        
        # 判断类型
        if has_video:
            article_type = 5
            type_name = '视频'
        elif has_audio:
            article_type = 7
            type_name = '音频'
        elif is_share:
            article_type = 11
            type_name = '分享'
        elif is_sticker:
            article_type = 10
            type_name = '贴图'
        else:
            article_type = 0
            type_name = '图文'
        
        return {
            'title': title,
            'type': article_type,
            'type_name': type_name,
            'features': {
                'has_video': has_video,
                'has_audio': has_audio,
                'has_images': has_images,
                'is_share': is_share,
                'is_sticker': is_sticker
            }
        }
    except Exception as e:
        return {
            'error': str(e),
            'type': None
        }

# 分析提供的文章
urls = [
    'https://mp.weixin.qq.com/s/jfhRhSD8CO4d6Op2ljuhVA',
    'https://mp.weixin.qq.com/s/cMB3xubsPlYRnS2gKKteIg',
    'https://mp.weixin.qq.com/s/dvL0lgjIAF7u_Vk36GKRTQ',
    'https://mp.weixin.qq.com/s/f7rLB4L9DGDOfkwCnbR67w',
    'https://mp.weixin.qq.com/s/4svk-UsVuyThdpwUJaYdRQ'
]

print("文章类型分析结果：")
print("=" * 80)

for i, url in enumerate(urls, 1):
    result = analyze_article_type(url)
    
    if 'error' in result:
        print(f"文章{i}: 访问失败 - {result['error']}")
    else:
        print(f"文章{i}: {result['title'][:60]}...")
        print(f"  类型: {result['type']} ({result['type_name']})")
        print(f"  特征: 视频={result['features']['has_video']}, "
              f"音频={result['features']['has_audio']}, "
              f"图片={result['features']['has_images']}, "
              f"分享={result['features']['is_share']}")
    print()
