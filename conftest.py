import pytest
import allure
from utils.logger import logger


def pytest_addoption(parser):
    """注册命令行参数"""
    parser.addoption(
        "--env", action="store", default="dev",
        help="指定运行环境: dev / test / prod"
    )


def pytest_configure(config):
    """pytest 启动时执行（早于所有 fixture）"""
    # 注册自定义标记
    config.addinivalue_line("markers", "smoke: 冒烟测试")
    config.addinivalue_line("markers", "regression: 回归测试")

    # 初始化环境配置（必须在所有 fixture 之前）
    env = config.getoption("--env", default="dev")
    from config.settings import get_settings
    get_settings(env)
    logger.info(f"✅ 当前运行环境: {env}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """用例失败时附加信息到 Allure"""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        logger.error(f"❌ 用例失败: {item.name}")
        allure.attach(
            f"失败用例: {item.name}\n详细日志见 reports/logs/",
            name="Failure Info",
            attachment_type=allure.attachment_type.TEXT,
        )