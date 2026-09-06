import requests
from utils.logger import logger
from config.settings import get_settings

class BaseAPI:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.base_url
        self.session = requests.Session()
        self.token = None

    def set_token(self, token: str):
        """设置鉴权 Token"""
        self.token = token

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        # 日志记录请求
        logger.info(f"→ {method} {url} | params={kwargs.get('params')} | body={kwargs.get('json')}")
        
        try:
            resp = self.session.request(method, url, headers=headers, timeout=10, **kwargs)
            logger.info(f"← {resp.status_code} | {resp.elapsed.total_seconds():.3f}s | {resp.text[:200]}")
            return resp
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            raise

    def get(self, path, **kwargs): return self.request("GET", path, **kwargs)
    def post(self, path, **kwargs): return self.request("POST", path, **kwargs)
    def put(self, path, **kwargs): return self.request("PUT", path, **kwargs)
    def delete(self, path, **kwargs): return self.request("DELETE", path, **kwargs)