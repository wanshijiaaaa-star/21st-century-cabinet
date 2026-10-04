from driver.wxarticle import WXArticleFetcher


def test_extract_nickname_from_html_decode_script():
    fetcher = WXArticleFetcher()
    html = 'var nickname = htmlDecode("示例公众号");'

    assert fetcher._extract_nickname(html) == "示例公众号"


def test_extract_nickname_decodes_entities_and_unicode_escapes():
    fetcher = WXArticleFetcher()
    html = r"var nickname = htmlDecode('研究\u9662 &amp; 社');"

    assert fetcher._extract_nickname(html) == "研究院 & 社"
