import requests
from utils.logger import logger
from config.settings import get_settings

# 日志脱敏：这些字段的值不落日志，避免密码/Token 泄露到日志文件
SENSITIVE_KEYS = {"password", "token", "access_token", "authorization"}


def _mask_sensitive(payload):
    """递归脱敏请求体中的敏感字段"""
    if isinstance(payload, dict):
        return {
            k: ("***" if str(k).lower() in SENSITIVE_KEYS else _mask_sensitive(v))
            for k, v in payload.items()
        }
    if isinstance(payload, list):
        return [_mask_sensitive(item) for item in payload]
    return payload


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

        body = kwargs.get("json") or kwargs.get("data")
        logger.info(f"→ {method} {url} | params={kwargs.get('params')} | body={_mask_sensitive(body)}")

        try:
            resp = self.session.request(
                method, url, headers=headers,
                timeout=self.settings.request_timeout, **kwargs
            )
            logger.info(f"← {resp.status_code} | {resp.elapsed.total_seconds():.3f}s | {resp.text[:200]}")
            return resp
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            raise

    def get(self, path, **kwargs): return self.request("GET", path, **kwargs)
    def post(self, path, **kwargs): return self.request("POST", path, **kwargs)
    def put(self, path, **kwargs): return self.request("PUT", path, **kwargs)
    def delete(self, path, **kwargs): return self.request("DELETE", path, **kwargs)
