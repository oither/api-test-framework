"""冒烟测试：验证框架基础联通性"""
import pytest
import allure


@allure.epic("博客系统API测试")
@allure.feature("冒烟验证")
@pytest.mark.smoke 
class TestSmoke:

    @allure.story("服务可用性")
    @allure.title("健康检查接口返回200")
    def test_health_check(self, auth_api):
        resp = auth_api.get("/")
        assert resp.status_code == 200

    @allure.story("认证模块")
    @allure.title("注册→登录→发文 完整链路")
    def test_full_chain(self, auth_api, article_api, db, registered_user):
        # 1. 登录
        login_resp = auth_api.login(
            registered_user["username"], registered_user["password"]
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        article_api.set_token(token)

        # 2. 发文
        create_resp = article_api.create(title="冒烟测试文章", content="验证链路")
        assert create_resp.status_code == 201
        article_id = create_resp.json()["id"]

        # 3. DB 校验
        article = db.get_article(article_id)
        assert article is not None
        assert article["title"] == "冒烟测试文章"

        # 4. 清理
        article_api.delete_article(article_id)