# -*- coding: utf-8 -*-
"""冒烟测试：ensure_mp_on_shelf 集成是否可用（不会真的写入，仅探测）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from core.wx.model.weread_mp import MpsWereadMP

wx = MpsWereadMP()
wx._load_weread_auth()
print("cookie len:", len(wx._weread_cookies), "| vid:", wx._weread_vid)
ok, detail = wx.ensure_mp_on_shelf("MP_WXS_1240574601", "央视新闻")
print("ensure result:", ok, "|", detail)
ok2, detail2 = wx.ensure_mp_on_shelf("3300008485", "普通书")
print("non-mp result:", ok2, "|", detail2)
