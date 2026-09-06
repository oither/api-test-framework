import sys
import time
import socket
import pytest
import allure
import requests
from pathlib import Path
from utils.logger import logger

VALID_ENVS = ["dev", "test", "prod"]


def pytest_addoption(parser):
    """注册命令行参数"""
    parser.addoption(
        "--env", action="store", default="dev", choices=VALID_ENVS,
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
    settings = get_settings(env)
    logger.info(f"✅ 当前运行环境: {env} | 被测服务: {settings.base_url}")


def _wait_service_ready(base_url: str, attempts: int = 10) -> bool:
    for _ in range(attempts):
        try:
            resp = requests.get(base_url, timeout=2)
            if resp.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def _write_allure_environment(config, settings):
    """写入 Allure 环境信息，报告首页可展示测试对象与运行环境"""
    alluredir = config.getoption("--alluredir", default=None)
    if not alluredir:
        return
    Path(alluredir).mkdir(parents=True, exist_ok=True)
    lines = [
        f"Environment={settings.env}",
        f"Base.URL={settings.base_url}",
        f"DB.Path={settings.db_path}",
        f"Python={sys.version.split()[0]}",
        f"Host={socket.gethostname()}",
    ]
    (Path(alluredir) / "environment.properties").write_text("\n".join(lines), encoding="utf-8")


def pytest_sessionstart(session):
    """会话开始：确认被测服务可用，避免几十条用例以连接错误失败后才暴露问题"""
    config = session.config
    if config.getoption("collectonly"):
        return
    from config.settings import get_settings
    settings = get_settings()

    _write_allure_environment(config, settings)

    if _wait_service_ready(settings.base_url):
        logger.info(f"✅ 被测服务就绪: {settings.base_url}")
    else:
        # fail-fast：服务不可达时终止会话，而不是让全部用例报连接错误
        raise pytest.UsageError(
            f"被测服务不可达: {settings.base_url}\n"
            "请先启动被测系统: cd blog-system-under-test && uvicorn app.main:app --reload"
        )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """用例失败时附加信息到 Allure（含 setup/teardown 阶段的错误）"""
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        logger.error(f"❌ 用例失败({report.when}): {item.name}")
        allure.attach(
            f"失败用例: {item.name} (阶段: {report.when})\n详细日志见 reports/logs/",
            name="Failure Info",
            attachment_type=allure.attachment_type.TEXT,
        )


def pytest_sessionfinish(session, exitstatus):
    if session.config.getoption("collectonly"):
        return
    alluredir = session.config.getoption("--alluredir", default=None)
    if alluredir and not exitstatus:
        logger.info(f"✅ 全部通过。Allure 结果: {alluredir}（allure serve {alluredir} 预览）")
    elif alluredir:
        logger.info(f"⚠️ 存在失败用例，Allure 结果: {alluredir}（allure serve {alluredir} 预览）")
