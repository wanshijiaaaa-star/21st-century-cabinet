from core.file import FileCrypto
from core.config import cfg
from core.redis_client import redis_client
import json

class KeyStore:
    key_file = "data/key.lic"
    redis_key = "werss:key_store:cookies"

    def __init__(self):
        self.store = FileCrypto(cfg.get("safe.lic_key", "store.csol.store.werss"))

    def save(self, text):
        items = []
        if type(text) != str:
            for item in text:
                # if item["domain"] == ".qq.com":
                #     continue
                items.append(item)
        text = json.dumps(items)

        # 优先保存到 Redis
        if redis_client.is_connected:
            try:
                redis_client._client.set(self.redis_key, text)
            except Exception:
                pass

        # 同时保存到本地文件作为备份
        self.store.encrypt_to_file(self.key_file, text.encode("utf-8"))

    def load(self):
        # 优先从 Redis 加载
        if redis_client.is_connected:
            try:
                data = redis_client._client.get(self.redis_key)
                if data:
                    items = json.loads(data)
                    new_items = self._filter_items(items)
                    return new_items
            except Exception:
                pass

        # Redis 不可用时从文件加载
        try:
            text = self.store.decrypt_from_file(self.key_file).decode("utf-8")
            items = json.loads(text)
            new_items = self._filter_items(items)
            return new_items
        except:
            return ""

    def _filter_items(self, items):
        """过滤 cookie items"""
        new_items = []
        for item in items:
            # if "domain" in item:
                # del item["domain"]
            if item['name'] == "_clck":
                continue
            if item['name'] == "token":
                continue
            new_items.append(item)
        return new_items


Store = KeyStore()