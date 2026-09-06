import allure
import pytest
from utils.data_loader import parametrize_from_yaml, resolve_placeholders


@allure.epic("博客系统API测试")
@allure.feature("文章模块")
class TestArticle:

    @allure.story("文章CRUD")
    @allure.title("{case[title]}")
    @parametrize_from_yaml("article_data.yaml")
    def test_article_scenarios(self, article_api, db, logged_in_user, request, case):
        """
        数据驱动的文章场景用例。
        user_article / another_logged_in_apis 按 action 惰性加载：
        列表、搜索、404 类用例不需要预置文章或第二用户，省掉每次用例的前置请求。
        """
        case = resolve_placeholders(case)
        action = case["action"]
        expected = case["expected_status"]
        user_article = None
        other_apis = None

        def _user_article() -> dict:
            nonlocal user_article
            if user_article is None:
                user_article = request.getfixturevalue("user_article")
            return user_article

        def _other_apis() -> dict:
            nonlocal other_apis
            if other_apis is None:
                other_apis = request.getfixturevalue("another_logged_in_apis")
            return other_apis

        # 确保当前是登录用户的 Token
        article_api.set_token(logged_in_user["token"])

        if action == "create":
            resp = article_api.create(
                title=case.get("article_title"),
                content=case.get("content"),
            )

        elif action == "create_no_auth":
            article_api.set_token(None)
            resp = article_api.create(
                title=case.get("article_title"),
                content=case.get("content"),
            )
            article_api.set_token(logged_in_user["token"])

        elif action == "list":
            resp = article_api.list(
                skip=case.get("skip", 0),
                limit=case.get("limit", 10),
            )

        elif action == "list_search":
            if case.get("expect_non_empty"):
                # 搜索命中用例：预置一篇标题含"测试文章"的文章，保证断言确定性
                _user_article()
            resp = article_api.list(search=case["search_keyword"])

        elif action == "detail_exist":
            resp = article_api.detail(_user_article()["id"])

        elif action == "detail":
            resp = article_api.detail(case["article_id"])

        elif action == "update_full":
            resp = article_api.update(
                _user_article()["id"],
                title=case["new_title"],
                content=case["new_content"],
            )

        elif action == "update_partial":
            resp = article_api.update(_user_article()["id"], title=case["new_title"])

        elif action == "update_by_other":
            other = _other_apis()["article"]
            resp = other.update(_user_article()["id"], title=case["new_title"])

        elif action == "update":
            resp = article_api.update(case["article_id"], title=case["new_title"])

        elif action == "update_no_auth":
            article_api.set_token(None)
            resp = article_api.update(case["article_id"], title="x")
            article_api.set_token(logged_in_user["token"])

        elif action == "delete_by_author":
            # 先创建一个临时文章再删
            tmp = article_api.create(title=f"待删除_{case['title']}", content="临时")
            tmp_id = tmp.json()["id"]
            resp = article_api.delete_article(tmp_id)
            if case.get("db_check_deleted"):
                assert db.get_article(tmp_id) is None, "删除后DB仍有记录"

        elif action == "delete_by_other":
            other = _other_apis()["article"]
            resp = other.delete_article(_user_article()["id"])

        elif action == "delete":
            resp = article_api.delete_article(case["article_id"])

        elif action == "delete_no_auth":
            article_api.set_token(None)
            resp = article_api.delete_article(case["article_id"])
            article_api.set_token(logged_in_user["token"])

        else:
            pytest.fail(f"未知 action: {action}")

        # ===== 断言 =====
        assert resp.status_code == expected, (
            f"[{case['title']}] 期望 {expected}, 实际 {resp.status_code}\n{resp.text}"
        )

        # DB 校验：创建成功
        if case.get("db_check") and expected == 201:
            article = db.get_article(resp.json()["id"])
            assert article is not None
            assert article["title"] == case["article_title"]
            assert article["author_id"] == db.get_user_by_username(
                logged_in_user["username"]
            )["id"], "author_id 应为当前登录用户"

        # DB 校验：更新成功
        if case.get("db_check") and expected == 200 and "update" in action:
            article = db.get_article(user_article["id"])
            assert article["title"] == case["new_title"]

        # exclude_unset 校验：仅改标题，内容不变
        if case.get("check_content_unchanged"):
            article = db.get_article(user_article["id"])
            assert article["content"] == "自动化测试内容", "未传的字段不应被修改"

        # 分页校验
        if case.get("check_pagination") and expected == 200:
            data = resp.json()
            assert isinstance(data, list), "列表接口应返回数组"
            max_items = case.get("max_items", 10)
            assert len(data) <= max_items, f"返回条数应不超过 {max_items}"

        # 搜索校验
        if case.get("expect_non_empty") and expected == 200:
            assert len(resp.json()) > 0, "搜索应有结果"
        if case.get("expect_empty") and expected == 200:
            assert len(resp.json()) == 0, "搜索应无结果"

    @allure.story("权限校验顺序")
    @allure.title("有Token + 不存在资源 → 404")
    def test_not_found_with_token(self, article_api, logged_in_user):
        article_api.set_token(logged_in_user["token"])
        resp = article_api.detail(999999)
        assert resp.status_code == 404

    @allure.story("权限校验顺序")
    @allure.title("有Token + 存在但非本人 → 403")
    def test_forbidden_other_user_article(
        self, article_api, logged_in_user, user_article, another_logged_in_apis
    ):
        other = another_logged_in_apis["article"]
        resp = other.update(user_article["id"], title="hacked")
        assert resp.status_code == 403
