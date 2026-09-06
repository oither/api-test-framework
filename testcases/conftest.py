import pytest
import allure
from api.auth_api import AuthAPI
from api.article_api import ArticleAPI
from api.comment_api import CommentAPI
from utils.db_helper import DBHelper
from utils.data_loader import generate_random_user
from config.settings import get_settings

@pytest.fixture(scope="session")
def settings():
    return get_settings()

@pytest.fixture(scope="session")
def db():
    return DBHelper()

@pytest.fixture(scope="session")
def auth_api():
    return AuthAPI()

@pytest.fixture(scope="session")
def article_api():
    return ArticleAPI()

@pytest.fixture(scope="session")
def comment_api():
    return CommentAPI()

@pytest.fixture
def registered_user(auth_api, db):
    """创建一个已注册的测试用户，用例结束后级联清理其全部数据"""
    user_data = generate_random_user()
    resp = auth_api.register(**user_data)
    assert resp.status_code == 201, f"注册用户失败: {resp.text}"

    yield user_data

    # 清理：直接删 DB 记录（博客系统无删除用户接口）
    db.delete_user_data(user_data["username"])

@pytest.fixture
def logged_in_user(auth_api, article_api, comment_api, registered_user):
    """返回已登录的用户信息（含 Token），并将 Token 注入所有 API 实例"""
    resp = auth_api.login(registered_user["username"], registered_user["password"])
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    token = resp.json()["access_token"]
    for api in (auth_api, article_api, comment_api):
        api.set_token(token)
    return {**registered_user, "token": token}

@pytest.fixture
def user_article(article_api, db, logged_in_user):
    """创建一个属于当前用户的文章"""
    resp = article_api.create(title=f"测试文章_{logged_in_user['username']}", content="自动化测试内容")
    assert resp.status_code == 201
    article = resp.json()
    yield article
    # 清理：先删评论再删文章。被测系统 DELETE /articles 不级联删评论，
    # 直接调接口删文章会留下孤儿评论记录
    db.delete_article_data(article["id"])

@pytest.fixture
def another_logged_in_apis(auth_api, db):
    """
    创建第二个已登录用户，返回独立的 API 实例。
    用于权限测试（如：非作者修改文章 → 403）。
    返回 dict: {"auth": AuthAPI, "article": ArticleAPI, "comment": CommentAPI, "user": {...}}
    """
    user_data = generate_random_user()
    reg_resp = auth_api.register(**user_data)
    assert reg_resp.status_code == 201, f"第二用户注册失败: {reg_resp.text}"
    resp = auth_api.login(user_data["username"], user_data["password"])
    assert resp.status_code == 200, f"第二用户登录失败: {resp.text}"
    token = resp.json()["access_token"]

    article_api = ArticleAPI()
    article_api.set_token(token)
    comment_api = CommentAPI()
    comment_api.set_token(token)

    yield {
        "auth": auth_api,
        "article": article_api,
        "comment": comment_api,
        "user": user_data,
        "token": token,
    }

    # 清理第二用户的数据
    db.delete_user_data(user_data["username"])

@pytest.fixture
def disabled_user(auth_api, db):
    """创建一个被禁用的用户（is_active=false），用于测试 403 场景"""
    user_data = generate_random_user()
    resp = auth_api.register(**user_data)
    assert resp.status_code == 201
    # 直接在 DB 中禁用该用户
    db.query(
        "UPDATE users SET is_active = 0 WHERE username = ?",
        (user_data["username"],),
    )
    yield user_data
    # 清理
    db.delete_user_data(user_data["username"])
