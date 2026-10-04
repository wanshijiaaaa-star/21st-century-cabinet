import socket

def scan_ports(ip, ports=None, timeout=1):
    if ports is None:
        ports = [21, 22, 23, 80, 135, 139, 443, 445, 3389, 8080]
    open_ports = []
    for port in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            result = s.connect_ex((ip, port))
            if result == 0:
                open_ports.append(port)
        except Exception:
            pass
        finally:
            s.close()
    return open_ports

def check_ftp_weak_password(ip, port=21):
    import ftplib
    try:
        ftp = ftplib.FTP()
        ftp.connect(ip, port, timeout=2)
        # 尝试匿名登录
        ftp.login()
        ftp.quit()
        return True
    except Exception:
        return False

def vulnerability_check(ip, open_ports):
    vulns = []
    # 检查高危端口
    high_risk_ports = {
        21: "FTP服务，可能存在弱口令或匿名访问",
        23: "Telnet服务，明文传输，易受攻击",
        445: "SMB服务，易受蠕虫攻击",
        3389: "远程桌面服务，建议加强认证"
    }
    for port in open_ports:
        if port in high_risk_ports:
            vulns.append(f"端口 {port}: {high_risk_ports[port]}")
        # 检查FTP弱口令
        if port == 21 and check_ftp_weak_password(ip, 21):
            vulns.append("FTP服务允许匿名登录，存在高危漏洞")
    return vulns

def get_security_advice(vulns):
    advice = []
    for v in vulns:
        if "FTP" in v:
            advice.append("建议：关闭FTP服务或禁止匿名登录，设置强密码。")
        if "Telnet" in v:
            advice.append("建议：关闭Telnet服务，使用SSH等安全协议替代。")
        if "SMB" in v:
            advice.append("建议：关闭不必要的SMB服务，及时打补丁。")
        if "远程桌面" in v:
            advice.append("建议：开启远程桌面双因素认证，限制访问来源。")
    return list(set(advice))  # 去重

if __name__ == "__main__":
    target_ip = input("请输入要检测的IP地址：")
    ports = input("请输入要扫描的端口（用逗号分隔，留空则扫描常见端口）：")
    if ports.strip():
        ports = [int(p.strip()) for p in ports.split(",")]
    else:
        ports = None
    open_ports = scan_ports(target_ip, ports)
    print(f"{target_ip} 开放的端口有: {open_ports}" if open_ports else "未检测到开放端口。")
    vulns = vulnerability_check(target_ip, open_ports)
    if vulns:
        print("检测到的安全风险：")
        for v in vulns:
            print(" -", v)
        advice = get_security_advice(vulns)
        if advice:
            print("\n安全建议：")
            for a in advice:
                print(" -", a)
    else:
        print("未检测到常见高危漏洞。")