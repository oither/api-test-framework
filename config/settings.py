import os
from pathlib import Path
from dotenv import load_dotenv


class Settings:
    def __init__(self, env: str = "dev"):
        self.env = env
        env_file = Path(__file__).parent / f".env.{env}"
        if not env_file.exists():
            raise FileNotFoundError(f"环境配置文件不存在: {env_file}")
        load_dotenv(env_file, override=True)

        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000")
        self.db_path = os.getenv("DB_PATH", "../blog-system-under-test/blog.db")
        self.token_expire_minutes = int(os.getenv("TOKEN_EXPIRE_MINUTES", 30))


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