"""
User-Agent 生成器模块
支持多浏览器类型、动态版本号、真实设备模拟
按市场份额权重分配，增强随机性和真实性
"""

import random


class UserAgentGenerator:
    """User-Agent 生成器，支持移动端和桌面端多浏览器类型"""
    
    def __init__(self):
        # 移动端浏览器权重分布
        self.mobile_browser_weights = {
            'chrome': 0.45,    # Chrome 占比最高
            'safari': 0.30,   # Safari iOS
            'firefox': 0.10,  # Firefox 移动版
            'edge': 0.08,     # Edge 移动版
            'opera': 0.05,    # Opera 移动版
            'qq': 0.02        # QQ浏览器
        }
        
        # 桌面端浏览器权重分布（模拟真实市场份额）
        self.desktop_browser_weights = {
            'chrome': 0.65,   # Chrome 占主导
            'edge': 0.12,     # Edge 
            'firefox': 0.08,  # Firefox
            'safari': 0.08,   # Safari macOS
            'opera': 0.05,    # Opera
            'qq': 0.02        # QQ浏览器
        }
    
    def get_realistic_user_agent(self, mobile_mode: bool = True) -> str:
        """
        获取更真实的User-Agent，支持多浏览器类型和动态版本号
        
        Args:
            mobile_mode: 是否为移动端模式
            
        Returns:
            生成的 User-Agent 字符串
        """
        if mobile_mode:
            ua=self._generate_mobile_ua()
            print(f"生成移动端 User-Agent: {ua}")
            return ua
        else:
            ua=self._generate_desktop_ua()
            print(f"生成桌面端 User-Agent: {ua}")
            return ua
    
    def _generate_mobile_ua(self) -> str:
        """生成移动端User-Agent"""
        browser_type = random.choices(
            list(self.mobile_browser_weights.keys()),
            weights=list(self.mobile_browser_weights.values())
        )[0]
        
        generators = {
            'chrome': self._generate_chrome_mobile_ua,
            'safari': self._generate_safari_mobile_ua,
            'firefox': self._generate_firefox_mobile_ua,
            'edge': self._generate_edge_mobile_ua,
            'opera': self._generate_opera_mobile_ua,
            'qq': self._generate_qq_mobile_ua
        }
        
        return generators[browser_type]()
    
    def _generate_desktop_ua(self) -> str:
        """生成桌面端User-Agent"""
        browser_type = random.choices(
            list(self.desktop_browser_weights.keys()),
            weights=list(self.desktop_browser_weights.values())
        )[0]
        
        generators = {
            'chrome': self._generate_chrome_desktop_ua,
            'edge': self._generate_edge_desktop_ua,
            'firefox': self._generate_firefox_desktop_ua,
            'safari': self._generate_safari_desktop_ua,
            'opera': self._generate_opera_desktop_ua,
            'qq': self._generate_qq_desktop_ua
        }
        
        return generators[browser_type]()
    
    # ========== 版本号生成 ==========
    
    def _get_chrome_version(self) -> str:
        """获取随机Chrome版本号（110-125）"""
        major = random.randint(110, 125)
        minor = random.randint(0, 9)
        build = random.randint(4000, 6500)
        patch = random.randint(0, 200)
        return f"{major}.{minor}.{build}.{patch}"
    
    def _get_firefox_version(self) -> str:
        """获取随机Firefox版本号（110-125）"""
        return str(random.randint(110, 125))
    
    def _get_safari_version(self) -> str:
        """获取随机Safari版本号"""
        version = random.randint(15, 17)
        minor = random.randint(0, 6)
        return f"{version}.{minor}"
    
    def _get_edge_version(self) -> str:
        """获取随机Edge版本号（110-125）"""
        major = random.randint(110, 125)
        minor = random.randint(0, 9)
        build = random.randint(1000, 2500)
        patch = random.randint(0, 100)
        return f"{major}.{minor}.{build}.{patch}"
    
    def _get_opera_version(self) -> str:
        """获取随机Opera版本号（90-110）"""
        major = random.randint(90, 110)
        minor = random.randint(0, 9)
        build = random.randint(4000, 5500)
        return f"{major}.{minor}.{build}.{major-13}"
    
    # ========== 操作系统版本 ==========
    
    def _get_android_version(self) -> str:
        """获取随机Android版本"""
        versions = ['10', '11', '12', '13', '14']
        weights = [0.15, 0.20, 0.30, 0.25, 0.10]
        return random.choices(versions, weights=weights)[0]
    
    def _get_ios_version(self) -> str:
        """获取随机iOS版本"""
        versions = ['15_0', '15_5', '16_0', '16_5', '17_0', '17_2', '17_4']
        weights = [0.10, 0.15, 0.15, 0.20, 0.20, 0.15, 0.05]
        return random.choices(versions, weights=weights)[0]
    
    def _get_windows_version(self) -> str:
        """获取随机Windows版本"""
        versions = [
            ('Windows NT 10.0; Win64; x64', 0.70),      # Windows 10/11 64位
            ('Windows NT 10.0; WOW64', 0.15),           # Windows 10/11 32位应用
            ('Windows NT 6.3; Win64; x64', 0.08),       # Windows 8.1
            ('Windows NT 6.1; Win64; x64', 0.05),       # Windows 7
            ('Windows NT 11.0; Win64; x64', 0.02),      # Windows 11
        ]
        return random.choices([v[0] for v in versions], weights=[v[1] for v in versions])[0]
    
    def _get_macos_version(self) -> str:
        """获取随机macOS版本"""
        versions = [
            ('10_15_7', 0.25),   # Catalina
            ('11_0', 0.15),      # Big Sur
            ('12_0', 0.20),      # Monterey
            ('13_0', 0.25),      # Ventura
            ('14_0', 0.15),      # Sonoma
        ]
        return random.choices([v[0] for v in versions], weights=[v[1] for v in versions])[0]
    
    def _get_linux_distro(self) -> str:
        """获取随机Linux发行版"""
        distros = [
            'X11; Linux x86_64',
            'X11; Ubuntu; Linux x86_64',
            'X11; Fedora; Linux x86_64',
            'X11; Arch Linux; Linux x86_64',
            'X11; Debian; Linux x86_64'
        ]
        return random.choice(distros)
    
    # ========== 设备型号 ==========
    
    def _get_android_device(self) -> str:
        """获取随机Android设备型号"""
        devices = [
            # 三星 Galaxy 系列
            'SM-G991B', 'SM-G998B', 'SM-G996B', 'SM-S908B', 'SM-S918B',
            'SM-G970F', 'SM-G973F', 'SM-G980F', 'SM-G988U', 'SM-G781B',
            # 小米系列
            'Mi 10', 'Mi 11', 'Mi 12', 'Mi 13', 'Redmi K50', 'Redmi K60',
            'Redmi Note 11', 'Redmi Note 12', 'Xiaomi 13', 'Xiaomi 14',
            # 华为系列
            'ELE-AL00', 'ANA-AL00', 'TAS-AL00', 'OCE-AN10', 'CET-AL00',
            # OPPO/Vivo
            'OPPO A5', 'OPPO Reno6', 'OPPO Find X3', 'Vivo X70', 'Vivo X80',
            # Google Pixel
            'Pixel 4', 'Pixel 5', 'Pixel 6', 'Pixel 6 Pro', 'Pixel 7', 'Pixel 7 Pro', 'Pixel 8',
            # OnePlus
            'OnePlus 8', 'OnePlus 9', 'OnePlus 10 Pro', 'OnePlus 11'
        ]
        return random.choice(devices)
    
    # ========== 移动端 UA 生成 ==========
    
    def _generate_chrome_mobile_ua(self) -> str:
        """生成Chrome移动端UA"""
        chrome_ver = self._get_chrome_version()
        android_ver = self._get_android_version()
        device = self._get_android_device()
        return f"Mozilla/5.0 (Linux; Android {android_ver}; {device}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Mobile Safari/537.36"
    
    def _generate_safari_mobile_ua(self) -> str:
        """生成Safari iOS移动端UA"""
        ios_ver = self._get_ios_version()
        safari_ver = self._get_safari_version()
        return f"Mozilla/5.0 (iPhone; CPU iPhone OS {ios_ver} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_ver} Mobile/15E148 Safari/604.1"
    
    def _generate_firefox_mobile_ua(self) -> str:
        """生成Firefox移动端UA"""
        firefox_ver = self._get_firefox_version()
        android_ver = self._get_android_version()
        return f"Mozilla/5.0 (Android {android_ver}; Mobile; rv:{firefox_ver}.0) Gecko/{firefox_ver}.0 Firefox/{firefox_ver}.0"
    
    def _generate_edge_mobile_ua(self) -> str:
        """生成Edge移动端UA"""
        edge_ver = self._get_edge_version()
        chrome_ver = self._get_chrome_version()
        android_ver = self._get_android_version()
        device = self._get_android_device()
        return f"Mozilla/5.0 (Linux; Android {android_ver}; {device}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Mobile Safari/537.36 EdgA/{edge_ver}"
    
    def _generate_opera_mobile_ua(self) -> str:
        """生成Opera移动端UA"""
        opera_ver = self._get_opera_version()
        chrome_ver = self._get_chrome_version()
        android_ver = self._get_android_version()
        device = self._get_android_device()
        return f"Mozilla/5.0 (Linux; Android {android_ver}; {device}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Mobile Safari/537.36 OPR/{opera_ver}"
    
    def _generate_qq_mobile_ua(self) -> str:
        """生成QQ浏览器移动端UA"""
        chrome_ver = self._get_chrome_version()
        android_ver = self._get_android_version()
        device = self._get_android_device()
        qq_ver = f"{random.randint(13, 15)}.{random.randint(0, 5)}.{random.randint(3000, 3500)}"
        return f"Mozilla/5.0 (Linux; Android {android_ver}; {device}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_ver} MQQBrowser/{qq_ver} Mobile Safari/537.36"
    
    # ========== 桌面端 UA 生成 ==========
    
    def _generate_chrome_desktop_ua(self) -> str:
        """生成Chrome桌面端UA"""
        chrome_ver = self._get_chrome_version()
        os_choices = [
            (self._get_windows_version(), 0.75),
            (f"Macintosh; Intel Mac OS X {self._get_macos_version()}", 0.15),
            (self._get_linux_distro(), 0.10)
        ]
        os_str = random.choices([o[0] for o in os_choices], weights=[o[1] for o in os_choices])[0]
        return f"Mozilla/5.0 ({os_str}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
    
    def _generate_edge_desktop_ua(self) -> str:
        """生成Edge桌面端UA"""
        edge_ver = self._get_edge_version()
        chrome_ver = self._get_chrome_version()
        win_ver = self._get_windows_version()
        return f"Mozilla/5.0 ({win_ver}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 Edg/{edge_ver}"
    
    def _generate_firefox_desktop_ua(self) -> str:
        """生成Firefox桌面端UA"""
        firefox_ver = self._get_firefox_version()
        os_choices = [
            (self._get_windows_version(), 0.60),
            (f"Macintosh; Intel Mac OS X {self._get_macos_version()}", 0.25),
            (self._get_linux_distro(), 0.15)
        ]
        os_str = random.choices([o[0] for o in os_choices], weights=[o[1] for o in os_choices])[0]
        return f"Mozilla/5.0 ({os_str}; rv:{firefox_ver}.0) Gecko/20100101 Firefox/{firefox_ver}.0"
    
    def _generate_safari_desktop_ua(self) -> str:
        """生成Safari桌面端UA（仅macOS）"""
        macos_ver = self._get_macos_version()
        safari_ver = self._get_safari_version()
        return f"Mozilla/5.0 (Macintosh; Intel Mac OS X {macos_ver}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{safari_ver} Safari/605.1.15"
    
    def _generate_opera_desktop_ua(self) -> str:
        """生成Opera桌面端UA"""
        opera_ver = self._get_opera_version()
        chrome_ver = self._get_chrome_version()
        os_choices = [
            (self._get_windows_version(), 0.70),
            (f"Macintosh; Intel Mac OS X {self._get_macos_version()}", 0.20),
            (self._get_linux_distro(), 0.10)
        ]
        os_str = random.choices([o[0] for o in os_choices], weights=[o[1] for o in os_choices])[0]
        return f"Mozilla/5.0 ({os_str}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 OPR/{opera_ver}"
    
    def _generate_qq_desktop_ua(self) -> str:
        """生成QQ浏览器桌面端UA"""
        chrome_ver = self._get_chrome_version()
        win_ver = self._get_windows_version()
        qq_ver = f"{random.randint(13, 15)}.{random.randint(0, 5)}.{random.randint(5000, 5500)}"
        return f"Mozilla/5.0 ({win_ver}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 QQBrowser/{qq_ver}"


# 全局实例，方便直接调用
_ua_generator = UserAgentGenerator()


def get_user_agent(mobile_mode: bool = True) -> str:
    """
    获取随机 User-Agent（便捷函数）
    
    Args:
        mobile_mode: 是否为移动端模式
        
    Returns:
        生成的 User-Agent 字符串
    """
    return _ua_generator.get_realistic_user_agent(mobile_mode)


# 示例用法
if __name__ == "__main__":
    print("=== 移动端 User-Agent 示例 ===")
    for i in range(5):
        print(f"{i+1}. {get_user_agent(mobile_mode=True)}")
    
    print("\n=== 桌面端 User-Agent 示例 ===")
    for i in range(5):
        print(f"{i+1}. {get_user_agent(mobile_mode=False)}")
