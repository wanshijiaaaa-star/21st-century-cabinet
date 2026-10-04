from tools.redis_server import run_redis_server
run_redis_server(config_path="config.yaml")
from os import remove
from driver.wxarticle import Web
from driver.success import Success
from driver.base import WX_API
from core.print import print_error,print_info,print_success
from jobs.fetch_no_article import fetch_articles_without_content
import base64
import re

from tools.fix import fix_html


def testWeb():
    urls="""
    https://mp.weixin.qq.com/s/puc5q9xFmfMSy3OyqeYxZA
    """.strip().split("\n")

    Web.FixArticle(urls=urls)
    pass

def testWx_Api():
      # 测试代码
    def login_success_callback(session_data, account_info):
        print("登录成功！")
        print(f"Token: {session_data.get('token')}")
        print(f"账号信息: {account_info}")
    
    def notice_callback(message):
        print(f"通知: {message}")
    
    from driver.wx_api import WeChat_api 
    # 保持程序运行以等待登录
    # 使用token登录
    haLogin=WeChat_api.login_with_token()
    if haLogin:
        print("已登录")
    else:
        print("未登录")

    # 获取二维码
    # result = get_qr_code(login_success_callback, notice_callback)
    result=WeChat_api.GetCode(login_success_callback, notice_callback)
    # print(f"二维码结果: {result}")


def testMarkDown():
    from core.models import Article
    from core.db import DB
    session=DB.get_session()
    art=session.query(Article).filter(Article.content != None).order_by(Article.id.desc()).first()
    # print(art.content)
    from core.content_format import  format_content
    content= format_content(art.content,"markdown")
    return content

def testMd2Doc():
    from tools.mdtools.export import export_md_to_doc
    doc_id="3918391364-2247502779_3,3076560530-2673097250_1,3076560530-2673097167_1,3076560530-2673097166_1".split(",")
    export_md_to_doc(mp_id="MP_WXS_3918391364",doc_id=doc_id,export_md=True, zip_file=False,remove_images=False,remove_links=False)



def testToken():
    from driver.auth import auth
    auth()
    # input("按任意键退出")

def testLogin():
    from driver.wx import WX_API
    from driver.success import Success
    # de_url=WX_API.Token(Success)
    # de_url=WX_API.GetCode(Success)
    # de_url=WX_API.wxLogin()
    # print(de_url)
    input("按任意键退出")
def testNotice():
    from jobs.notice import sys_notice
    text="""
    消息测试<font color="warning">132例</font>，请相关同事注意。
> 类型:<font color="comment">用户反馈</font>
> 普通用户反馈:<font color="comment">117例</font>
> VIP用户反馈:<font color="comment">15例</font>
"""
    sys_notice(text,"测试通知","测试通知","测试通知")

def test_fetch_articles_without_content():
    from jobs.fetch_no_article import fetch_articles_without_content,start_sync_content
    fetch_articles_without_content()
    start_sync_content()
    input("按任意键退出")
def test_Gather_Article():
    from core.wx.base import WxGather
    ga=WxGather().Model("web")
    urls=[
        # "https://mp.weixin.qq.com/s/-J7tiMKzYSr60thWKtFbYQ",
        "https://mp.weixin.qq.com/s/z51LqW6rEE7uqUMGARPElA",
        #   "https://mp.weixin.qq.com/s/r8AgtesEVSnV-QpEbpb8-Q",
        #   "https://mp.weixin.qq.com/s?__biz=MzI3MTQzNjYxNw==&mid=2247912631&idx=1&sn=6a60ca17a85b2aac8c1236c9df8cbe36&scene=21&poc_token=HNMGC2mj1itdGEMeEq01KxIvG5QUmsY-ZUxsdewX"
        ]
    for url in urls:
        content= ga.content_extract(url)
        content=f'''
        <!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试文章</title>
</head>
<body>{content}</body>
</html>
        '''
        with open("./static/test.html", "w", encoding="utf-8") as f:
            f.write(content)
        text_fix()
        print(content)

def text_fix():
    with open("./static/test.html", "r", encoding="utf-8") as f:
        content=f.read()
    with open("./static/fix.html", "w", encoding="utf-8") as f:
        f.write(fix_html(content))
    
def test_screenshot():
    """测试截图功能,使用 PlaywrightController 统一管理资源"""
    from driver.playwright_driver import PlaywrightController
    from playwright.sync_api import TimeoutError
    
    controller = PlaywrightController()
    
    try:
        # 启动浏览器
        page = controller.start_browser(headless=False)
        
        # 导航到目标页面
        page.goto('https://mp.weixin.qq.com/')
        
        # 查找图片元素
        image_element = page.query_selector('.login__type__container__scan__qrcode')
        path='./static/qrcode.png'
        target_substring="home"
        
        if image_element:
            # 截图保存
            image_element.screenshot(path=path)
            print(f'图片已成功截取并保存为 {path}')
        else:
            print('未找到指定的图片元素')
        
        navigation_completed = False

        # 监听页面导航事件
        def handle_frame_navigated(frame):
            nonlocal navigation_completed
            current_url = frame.url
            if target_substring in current_url and not navigation_completed:
                print(f"页面已成功跳转到包含 '{target_substring}' 的URL: {current_url}")
                navigation_completed = True
        
        page.on('framenavigated', handle_frame_navigated)
        page.wait_for_event("framenavigated")
        print(page.url)
        
    finally:
        # 确保资源被正确清理
        controller.cleanup()



def test_anti_bot_detection():
    """
    测试 Playwright 反人机检测能力
    访问多个反爬虫检测网站，验证浏览器指纹伪装效果
    """
    from playwright.sync_api import sync_playwright
    from driver.anti_crawler_config import AntiCrawlerConfig
    import time
    
    # 反人机检测测试网站列表
    test_sites = [
        {
            "name": "Sannysoft Bot Detection",
            "url": "https://bot.sannysoft.com/",
            "desc": "全面的机器人检测，检查 WebDriver、自动化标志等"
        },
        {
            "name": "Are You Headless",
            "url": "https://arh.antoinevastel.com/bots/areyouheadless",
            "desc": "检测是否为无头浏览器模式"
        },
        {
            "name": "Pixelscan",
            "url": "https://pixelscan.net/",
            "desc": "浏览器指纹检测，包括 Canvas、WebGL、音频指纹"
        },
        {
            "name": "NowSecure",
            "url": "https://nowsecure.nl/",
            "desc": "检测自动化工具和爬虫"
        },
        {
            "name": "Bot Incolumitas",
            "url": "https://bot.incolumitas.com/",
            "desc": "机器人检测，检查多种自动化特征"
        },
        {
            "name": "BrowserScan",
            "url": "https://www.browserscan.net/",
            "desc": "浏览器特征扫描"
        }
    ]
    
    print("=" * 60)
    print("Playwright 反人机检测能力测试")
    print("=" * 60)
    
    anti_crawler = AntiCrawlerConfig()
    
    with sync_playwright() as p:
        # 启动 Chromium 浏览器（带反检测配置）
        print("\n[*] 启动 Chromium 浏览器...")
        
        launch_options = {
            "headless": True,  # 使用有头模式更容易过检测
            "args": [
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-webrtc",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-background-networking",
                "--disable-sync",
                "--no-first-run",
                "--disable-default-apps",
                "--no-default-browser-check",
                "--disable-dev-shm-usage",
            ]
        }
        
        browser = p.chromium.launch(**launch_options)
        
        # 获取反爬虫配置
        context_options = anti_crawler.get_anti_crawler_config(mobile_mode=True)
        context = browser.new_context(**context_options)
        page = context.new_page()
        
        # 注入反检测脚本
        page.add_init_script(anti_crawler.get_init_script())
        page.evaluate(anti_crawler.get_behavior_script())
        
        print("[*] 反检测脚本已注入")
        print("[*] 开始访问测试网站...\n")
        
        results = []  # 存储每个网站的测试结果
        
        for site in test_sites:
            try:
                print(f"\n{'='*50}")
                print(f"[*] 测试: {site['name']}")
                print(f"    URL: {site['url']}")
                print(f"    描述: {site['desc']}")
                print("-" * 50)
                
                page.goto(site['url'], timeout=30000, wait_until="domcontentloaded")
                
                # 等待页面加载
                time.sleep(5)
                
                # 获取页面标题
                title = page.title()
                print(f"    页面标题: {title}")
                
                # 截图保存
                screenshot_path = f"./static/anti_bot_{site['name'].lower().replace(' ', '_')}.png"
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"    截图已保存: {screenshot_path}")
                
                # 检测关键指标
                print("\n    [关键指标检测]")
                
                # 检测 webdriver 属性
                webdriver_value = page.evaluate("() => navigator.webdriver")
                webdriver_ok = webdriver_value is None or webdriver_value == False
                print(f"    - navigator.webdriver: {webdriver_value} {'✅' if webdriver_ok else '❌'}")
                
                # 检测 plugins
                plugins_count = page.evaluate("() => navigator.plugins.length")
                plugins_ok = plugins_count > 0
                print(f"    - navigator.plugins.length: {plugins_count} {'✅' if plugins_ok else '❌'}")
                
                # 检测 languages
                languages = page.evaluate("() => navigator.languages")
                languages_ok = languages and len(languages) > 0
                print(f"    - navigator.languages: {languages} {'✅' if languages_ok else '❌'}")
                
                # 检测 chrome 对象
                has_chrome = page.evaluate("() => typeof window.chrome !== 'undefined'")
                print(f"    - window.chrome: {has_chrome} {'✅' if has_chrome else '❌'}")
                
                # 检测 User-Agent
                ua = page.evaluate("() => navigator.userAgent")
                print(f"    - User-Agent: {ua[:60]}...")
                
                # 检测 WebGL 渲染器
                webgl_renderer = page.evaluate("""
                    () => {
                        const canvas = document.createElement('canvas');
                        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                        if (gl) {
                            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                            return debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : 'N/A';
                        }
                        return 'WebGL not supported';
                    }
                """)
                webgl_ok = webgl_renderer and webgl_renderer != 'N/A'
                print(f"    - WebGL Renderer: {webgl_renderer[:50]}... {'✅' if webgl_ok else '❌'}")
                
                # 检测自动化痕迹
                playwright_exists = page.evaluate("() => typeof window.__playwright !== 'undefined'")
                puppeteer_exists = page.evaluate("() => typeof window.__puppeteer !== 'undefined'")
                selenium_exists = page.evaluate("() => typeof window.__selenium !== 'undefined'")
                auto_ok = not (playwright_exists or puppeteer_exists or selenium_exists)
                print(f"    - 自动化痕迹: Playwright={playwright_exists}, Puppeteer={puppeteer_exists}, Selenium={selenium_exists} {'✅' if auto_ok else '❌'}")
                
                # 计算得分
                score = sum([webdriver_ok, plugins_ok, languages_ok, has_chrome, webgl_ok, auto_ok])
                site_result = {
                    "name": site['name'],
                    "url": site['url'],
                    "score": score,
                    "total": 6,
                    "details": {
                        "webdriver": webdriver_ok,
                        "plugins": plugins_ok,
                        "languages": languages_ok,
                        "chrome": has_chrome,
                        "webgl": webgl_ok,
                        "auto": auto_ok
                    }
                }
                results.append(site_result)
                
                print(f"\n    得分: {score}/6")
                print(f"\n    [!] 请手动检查页面: {site['url']}")
                print("    浏览器将保持打开状态供您查看完整报告")
                
                
            except Exception as e:
                print(f"    [错误] 访问失败: {str(e)}")
                results.append({
                    "name": site['name'],
                    "url": site['url'],
                    "score": 0,
                    "total": 6,
                    "error": str(e)
                })
                continue
        
        # 汇总结果
        print("\n" + "=" * 60)
        print("[*] 测试完成! 汇总报告:")
        print("=" * 60)
        
        for r in results:
            status = "✅" if r['score'] >= 5 else "⚠️" if r['score'] >= 3 else "❌"
            print(f"{status} {r['name']}: {r['score']}/{r['total']}")
        
        total_score = sum(r['score'] for r in results)
        total_possible = sum(r['total'] for r in results)
        percentage = (total_score / total_possible) * 100 if total_possible > 0 else 0
        
        print("\n" + "-" * 40)
        print(f"总分: {total_score}/{total_possible} ({percentage:.1f}%)")
        print("-" * 40)
        
        print("\n提示:")
        print("1. 检查截图文件了解各网站的检测结果")
        print("2. 好的检测结果应该显示:")
        print("   - navigator.webdriver = undefined")
        print("   - 有合理的 plugins 数量 (>0)")
        print("   - window.chrome 对象存在")
        print("   - WebGL 指纹正常")
        print("   - 无自动化框架痕迹")
        print("   - 各项检测显示为绿色/通过")
        
        context.close()
        browser.close()


def test_anti_bot_quick():
    """
    快速测试 Playwright 反人机检测（仅访问关键网站）
    """
    from driver.playwright_driver import PlaywrightController
    import time
    
    print("=" * 60)
    print("快速反人机检测测试")
    print("=" * 60)
    
    controller = PlaywrightController()
    
    try:
        # 启动浏览器（启用反爬虫）
        page = controller.start_browser(
            headless=True,
            mobile_mode=True,
            dis_image=False,
            anti_crawler=True
        )
        
        # 测试网站
        test_url = "https://bot.sannysoft.com/"
        print(f"\n[*] 访问: {test_url}")
        
        page.goto(test_url, timeout=30000)
        time.sleep(5)
        
        # 检测关键指标
        print("\n" + "=" * 60)
        print("[检测结果]")
        print("=" * 60)
        
        # WebDriver 检测
        webdriver = page.evaluate("() => navigator.webdriver")
        webdriver_status = "✅ PASS" if webdriver is None or webdriver == False else "❌ FAIL"
        print(f"  WebDriver: {webdriver} {webdriver_status}")
        
        # Plugins 检测
        plugins = page.evaluate("() => navigator.plugins.length")
        plugins_status = "✅ PASS" if plugins > 0 else "❌ FAIL"
        print(f"  Plugins: {plugins} {plugins_status}")
        
        # Languages 检测
        languages = page.evaluate("() => navigator.languages")
        languages_status = "✅ PASS" if languages and len(languages) > 0 else "❌ FAIL"
        print(f"  Languages: {languages} {languages_status}")
        
        # Chrome 对象检测
        has_chrome = page.evaluate("() => typeof window.chrome !== 'undefined'")
        chrome_status = "✅ PASS" if has_chrome else "❌ FAIL"
        print(f"  Chrome Object: {has_chrome} {chrome_status}")
        
        # Permissions API
        permissions_status = page.evaluate("""
            () => {
                try {
                    return typeof navigator.permissions.query === 'function';
                } catch(e) {
                    return false;
                }
            }
        """)
        perm_status = "✅ PASS" if permissions_status else "❌ FAIL"
        print(f"  Permissions API: {permissions_status} {perm_status}")
        
        # WebGL Vendor
        webgl_vendor = page.evaluate("""
            () => {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (gl) {
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    return debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : 'N/A';
                }
                return 'WebGL not supported';
            }
        """)
        webgl_status = "✅ PASS" if webgl_vendor and webgl_vendor != 'N/A' else "❌ FAIL"
        print(f"  WebGL Vendor: {webgl_vendor} {webgl_status}")
        
        # WebGL Renderer
        webgl_renderer = page.evaluate("""
            () => {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (gl) {
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    return debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : 'N/A';
                }
                return 'WebGL not supported';
            }
        """)
        print(f"  WebGL Renderer: {webgl_renderer}")
        
        # User Agent
        ua = page.evaluate("() => navigator.userAgent")
        print(f"  User-Agent: {ua[:80]}...")
        
        # Platform
        platform = page.evaluate("() => navigator.platform")
        print(f"  Platform: {platform}")
        
        # Hardware Concurrency
        cores = page.evaluate("() => navigator.hardwareConcurrency")
        print(f"  CPU Cores: {cores}")
        
        # Device Memory
        memory = page.evaluate("() => navigator.deviceMemory")
        print(f"  Device Memory: {memory} GB")
        
        # 自动化痕迹检测
        playwright_exists = page.evaluate("() => typeof window.__playwright !== 'undefined'")
        puppeteer_exists = page.evaluate("() => typeof window.__puppeteer !== 'undefined'")
        selenium_exists = page.evaluate("() => typeof window.__selenium !== 'undefined'")
        
        auto_status = "✅ PASS" if not (playwright_exists or puppeteer_exists or selenium_exists) else "❌ FAIL"
        print(f"\n  自动化框架痕迹: Playwright={playwright_exists}, Puppeteer={puppeteer_exists}, Selenium={selenium_exists} {auto_status}")
        
        # 统计结果
        print("\n" + "=" * 60)
        pass_count = sum([
            webdriver is None or webdriver == False,
            plugins > 0,
            languages and len(languages) > 0,
            has_chrome,
            permissions_status,
            webgl_vendor and webgl_vendor != 'N/A',
            not (playwright_exists or puppeteer_exists or selenium_exists)
        ])
        total = 7
        print(f"[总计] 通过: {pass_count}/{total}")
        print("=" * 60)
        
        # 截图
        screenshot_path = "./static/anti_bot_quick.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n截图已保存: {screenshot_path}")
        
        
    finally:
        controller.cleanup()

def switchaccount():
    import asyncio
    from driver.base import WX_API
    if not asyncio.run(WX_API.switch_account()):
        from jobs.failauth import send_wx_code
        import threading
        # threading.Thread(target=send_wx_code,args=(f"公众号平台登录失效,请重新登录",)).start()
        input("按回车键退出")
    pass
if __name__=="__main__":
    # testLogin()
    # test_anti_bot_quick()
    # test_anti_bot_detection()
    # test_screenshot()
    # test_Gather_Article()
    # text_fix()    
    switchaccount()
    # testWx_Api()
    # test_fetch_articles_without_content()
    # testWeb()
    # testNotice()
    # testMd2Doc()
    # testToken()
    # testMarkDown()
    # test_anti_bot_detection()  # 测试反人机检测
    # test_anti_bot_quick()       # 快速测试