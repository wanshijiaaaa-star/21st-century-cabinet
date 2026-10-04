import asyncio
import unittest
from unittest.mock import patch

from apis.weread import (
    WereadCollectRequest,
    WereadCookieRequest,
    WereadMPTestRequest,
    clear_weread_cookie,
    collect_weread_notes,
    get_weread_status,
    save_weread_cookie,
    test_weread_mp_connection,
)


class WereadConfigAPITest(unittest.TestCase):
    @patch("apis.weread._save_weread_data")
    @patch("apis.weread._load_weread_data", return_value={})
    def test_save_cookie_persists_article_list_ticket(self, _load, save):
        request = WereadCookieRequest(
            cookie="wr_vid=123; wr_skey=skey",
            ticket="ticket-value",
        )

        asyncio.run(save_weread_cookie(request, current_user={"id": "test"}))

        saved = save.call_args.args[0]
        self.assertEqual(saved["vid"], "123")
        self.assertEqual(saved["ticket"], "ticket-value")

    @patch("apis.weread.app_cfg.get")
    @patch("apis.weread._load_weread_data")
    def test_status_reports_mp_mode_without_requiring_ticket(self, load, config_get):
        load.return_value = {
            "cookie": "wr_vid=123; wr_skey=skey",
            "vid": "123",
            "ticket": "",
        }
        values = {
            "weread.cookie": "",
            "weread.ticket": "",
            "weread.vid": "",
            "gather.model": "weread_mp",
        }
        config_get.side_effect = lambda key, default="": values.get(key, default)

        response = asyncio.run(get_weread_status(current_user={"id": "test"}))

        self.assertTrue(response["data"]["configured"])
        self.assertTrue(response["data"]["mp_configured"])
        self.assertFalse(response["data"]["has_ticket"])
        self.assertEqual(response["data"]["gather_model"], "weread_mp")

    @patch("apis.weread.app_cfg.get")
    @patch("apis.weread._load_weread_data", return_value={})
    def test_status_reports_environment_managed_credentials(self, _load, config_get):
        values = {
            "weread.cookie": "wr_vid=456; wr_skey=env",
            "weread.ticket": "env-ticket",
            "weread.vid": "456",
        }
        config_get.side_effect = lambda key, default="": values.get(key, default)

        response = asyncio.run(get_weread_status(current_user={"id": "test"}))

        self.assertTrue(response["data"]["configured"])
        self.assertTrue(response["data"]["mp_configured"])
        self.assertTrue(response["data"]["managed_by_config"])

    @patch("apis.weread._save_weread_data")
    @patch("apis.weread._load_weread_data")
    def test_ticket_update_reuses_saved_cookie(self, load, save):
        load.return_value = {
            "cookie": "wr_vid=123; wr_skey=skey",
            "vid": "123",
            "ticket": "old-ticket",
        }
        request = WereadCookieRequest(ticket="new-ticket")

        asyncio.run(save_weread_cookie(request, current_user={"id": "test"}))

        saved = save.call_args.args[0]
        self.assertEqual(saved["cookie"], "wr_vid=123; wr_skey=skey")
        self.assertEqual(saved["ticket"], "new-ticket")

    @patch("apis.weread._save_weread_data")
    @patch("apis.weread._load_weread_data")
    def test_clear_cookie_also_clears_ticket(self, load, save):
        load.return_value = {
            "cookie": "wr_vid=123; wr_skey=skey",
            "vid": "123",
            "ticket": "ticket-value",
        }

        asyncio.run(clear_weread_cookie(current_user={"id": "test"}))

        saved = save.call_args.args[0]
        self.assertEqual(saved["cookie"], "")
        self.assertEqual(saved["vid"], "")
        self.assertEqual(saved["ticket"], "")

    @patch("apis.weread.app_cfg.get", return_value="env-value")
    @patch("apis.weread._save_weread_data")
    def test_clear_rejects_environment_managed_credentials(self, save, _config_get):
        response = asyncio.run(clear_weread_cookie(current_user={"id": "test"}))

        self.assertEqual(response["code"], 409)
        save.assert_not_called()

    @patch("core.wx.model.weread_mp.MpsWereadMP")
    def test_mp_connection_reports_api_auth_error(self, collector_class):
        from core.wx.model.weread_mp import WereadMPAPIError

        collector = collector_class.return_value
        collector._get_mp_articles_page.side_effect = WereadMPAPIError(
            -2041,
            "ticket expired",
            retriable=False,
        )

        response = asyncio.run(test_weread_mp_connection(
            WereadMPTestRequest(mp_id="MP_WXS_1"),
            current_user={"id": "test"},
        ))

        self.assertEqual(response["code"], 400)
        self.assertEqual(response["data"]["code"], -2041)

    @patch("core.db.DB.add_article", return_value=True)
    @patch("core.wx.model.weread.MpsWeread")
    def test_manual_note_collect_preserves_normalized_publish_time(self, collector_class, add_article):
        collector = collector_class.return_value
        collector._weread_cookies = "wr_vid=123; wr_skey=skey"
        collector._weread_ticket = "ticket-value"

        def collect(**kwargs):
            kwargs["CallBack"]({
                "id": "article-1",
                "mp_id": "MP_WXS_1",
                "title": "Article title",
                "url": "https://mp.weixin.qq.com/s/article-1",
                "pic_url": "https://example.test/cover.jpg",
                "content": "<p>Full text</p>",
                "publish_time": 1778580002,
            })

        collector.get_Articles.side_effect = collect
        request = WereadCollectRequest(mp_id="MP_WXS_1", mp_name="Feed")

        response = asyncio.run(
            collect_weread_notes(request, current_user={"id": "test"})
        )

        self.assertEqual(response["data"]["collected"], 1)
        saved = add_article.call_args.args[0]
        self.assertEqual(saved["publish_time"], 1778580002)


if __name__ == "__main__":
    unittest.main()
