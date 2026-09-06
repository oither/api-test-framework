import sys
from loguru import logger

# 移除默认 handler，自定义格式
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | {message}"
)
logger.add(
    "reports/logs/test_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8"
)