"""
测试脚本 - 演示如何使用文章类型检测器
"""

from article_type_detector_enhanced import ArticleTypeDetector, print_result


def test_single_url():
    """测试单个URL检测"""
    print("=" * 80)
    print("测试1: 单个URL检测")
    print("=" * 80)
    
    detector = ArticleTypeDetector()
    url = 'https://mp.weixin.qq.com/s/jfhRhSD8CO4d6Op2ljuhVA'
    
    result = detector.detect_type(url)
    print_result(result)
    print()


def test_batch_urls():
    """测试批量URL检测"""
    print("=" * 80)
    print("测试2: 批量URL检测")
    print("=" * 80)
    
    urls = [
        'https://mp.weixin.qq.com/s/jfhRhSD8CO4d6Op2ljuhVA',
        'https://mp.weixin.qq.com/s/cMB3xubsPlYRnS2gKKteIg',
        'https://mp.weixin.qq.com/s/dvL0lgjIAF7u_Vk36GKRTQ',
        'https://mp.weixin.qq.com/s/f7rLB4L9DGDOfkwCnbR67w',
        'https://mp.weixin.qq.com/s/4svk-UsVuyThdpwUJaYdRQ'
    ]
    
    detector = ArticleTypeDetector()
    results = detector.batch_detect(urls)
    
    for i, result in enumerate(results, 1):
        print_result(result, i)
        print()


def test_html_content():
    """测试从HTML内容检测"""
    print("=" * 80)
    print("测试3: 从HTML内容检测")
    print("=" * 80)
    
    # 模拟一个包含视频的HTML内容
    html_with_video = """
    <!DOCTYPE html>
    <html>
    <head><title>视频文章测试</title></head>
    <body>
        <div class="rich_media_content">
            <h1>这是一个视频文章</h1>
            <p>这是文章内容</p>
            <iframe class="video_iframe" src="https://v.qq.com/xxx"></iframe>
        </div>
    </body>
    </html>
    """
    
    # 模拟一个包含音频的HTML内容
    html_with_audio = """
    <!DOCTYPE html>
    <html>
    <head><title>音频文章测试</title></head>
    <body>
        <div class="rich_media_content">
            <h1>这是一个音频文章</h1>
            <p>这是文章内容</p>
            <mpvoice src="xxx"></mpvoice>
        </div>
    </body>
    </html>
    """
    
    # 模拟一个图文文章
    html_image_text = """
    <!DOCTYPE html>
    <html>
    <head><title>图文文章测试</title></head>
    <body>
        <div class="rich_media_content">
            <h1>这是一个图文文章</h1>
            <p>这是第一段内容，包含一些文字。</p>
            <p>这是第二段内容，包含更多文字。</p>
            <img class="rich_pages" src="https://mmbiz.qpic.cn/xxx.jpg">
            <p>这是第三段内容。</p>
        </div>
    </body>
    </html>
    """
    
    detector = ArticleTypeDetector()
    
    print("检测视频文章:")
    result = detector.detect_type_from_html(html_with_video)
    print_result(result)
    print()
    
    print("检测音频文章:")
    result = detector.detect_type_from_html(html_with_audio)
    print_result(result)
    print()
    
    print("检测图文文章:")
    result = detector.detect_type_from_html(html_image_text)
    print_result(result)
    print()


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "微信公众号文章类型检测器测试" + " " * 28 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")
    
    # 测试从HTML内容检测（不需要网络）
    test_html_content()
    
    # 测试单个URL检测（需要网络）
    # test_single_url()
    
    # 测试批量URL检测（需要网络）
    # test_batch_urls()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)
    print()
    print("提示:")
    print("1. test_html_content() - 测试从HTML内容检测（无需网络）")
    print("2. test_single_url() - 测试单个URL检测（需要网络）")
    print("3. test_batch_urls() - 测试批量URL检测（需要网络）")
    print()


if __name__ == '__main__':
    main()
