import sys
from pathlib import Path
from loguru import logger

# 日志目录锚定项目根，与 DB_PATH 同策略：从任意目录运行 pytest 都落对位置
LOG_DIR = Path(__file__).parent.parent / "reports" / "logs"

# 移除默认 handler，自定义格式
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | {message}"
)
logger.add(
    str(LOG_DIR / "test_{time:YYYY-MM-DD}.log"),
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8"
)
