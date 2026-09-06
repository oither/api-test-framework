import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录：config/ 的上一级。所有相对路径都锚定到这里，
# 保证从任意工作目录运行 pytest，DB 与日志都落在项目内
PROJECT_ROOT = Path(__file__).parent.parent


def _resolve_path(path: str) -> str:
    """相对路径 → 以项目根为基准的绝对路径；绝对路径原样返回"""
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return str(p.resolve())


class Settings:
    def __init__(self, env: str = "dev"):
        self.env = env
        env_file = Path(__file__).parent / f".env.{env}"
        if not env_file.exists():
            raise FileNotFoundError(f"环境配置文件不存在: {env_file}")
        load_dotenv(env_file, override=True)

        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000")
        self.db_path = _resolve_path(os.getenv("DB_PATH", "../blog-system-under-test/blog.db"))
        self.request_timeout = float(os.getenv("REQUEST_TIMEOUT", 10))


_settings_instance = None


def get_settings(env: str = None) -> Settings:
    """
    获取配置单例。
    - 传入 env：强制重建（用于 pytest_configure 初始化）
    - 不传 env：返回已有实例（用于业务代码）
    """
    global _settings_instance
    if env is not None:
        _settings_instance = Settings(env)
    elif _settings_instance is None:
        _settings_instance = Settings("dev")
    return _settings_instance
