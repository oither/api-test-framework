import allure
import pytest
from utils.data_loader import parametrize_from_yaml, resolve_placeholders


@allure.epic("博客系统API测试")
@allure.feature("评论模块")
class TestComment:

    @allure.story("评论CRUD")
    @allure.title("{case[title]}")
    @parametrize_from_yaml("comment_data.yaml")
    def test_comment_scenarios(
        self, comment_api, article_api, auth_api, db,
        logged_in_user, user_article, another_logged_in_apis, case
    ):
        case = resolve_placeholders(case)
        action = case["action"]
        expected = case["expected_status"]
        article_id = case.get("article_id", user_article["id"])

        comment_api.set_token(logged_in_user["token"])

        if action == "create":
            resp = comment_api.create(article_id, content=case.get("content"))

        elif action == "create_no_auth":
            comment_api.set_token(None)
            resp = comment_api.create(user_article["id"], content=case["content"])
            comment_api.set_token(logged_in_user["token"])

        elif action == "list_with_comments":
            # 先创建一条评论
            comment_api.create(user_article["id"], content="预置评论")
            resp = comment_api.list(user_article["id"])

        elif action == "list_empty":
            # 创建一篇新文章（无评论）
            tmp = article_api.create(title="无评论文章", content="test")
            resp = comment_api.list(tmp.json()["id"])
            article_api.delete_article(tmp.json()["id"])

        elif action == "list":
            resp = comment_api.list(article_id)

        elif action == "delete_by_owner":
            # 先创建评论，再删除
            c = comment_api.create(user_article["id"], content="待删除评论")
            cid = c.json()["id"]
            resp = comment_api.delete_comment(user_article["id"], cid)
            if case.get("db_check_deleted"):
                rows = db.query(
                    "SELECT * FROM comments WHERE id = ?", (cid,)
                )
                assert len(rows) == 0, "删除后DB仍有评论记录"

        elif action == "delete_by_other":
            # 用户A创建评论，用户B尝试删除
            c = comment_api.create(user_article["id"], content="A的评论")
            cid = c.json()["id"]
            other = another_logged_in_apis["comment"]
            resp = other.delete_comment(user_article["id"], cid)

        elif action == "delete_cross_article":
            # 在文章1创建评论，尝试通过文章2的路径删除 → 404
            c = comment_api.create(user_article["id"], content="跨文章测试")
            cid = c.json()["id"]
            tmp = article_api.create(title="另一篇文章", content="test")
            other_article_id = tmp.json()["id"]
            resp = comment_api.delete_comment(other_article_id, cid)
            article_api.delete_article(other_article_id)

        elif action == "delete":
            resp = comment_api.delete_comment(article_id, case["comment_id"])

        elif action == "delete_no_auth":
            comment_api.set_token(None)
            resp = comment_api.delete_comment(user_article["id"], case["comment_id"])
            comment_api.set_token(logged_in_user["token"])

        else:
            pytest.fail(f"未知 action: {action}")

        # ===== 断言 =====
        assert resp.status_code == expected, (
            f"[{case['title']}] 期望 {expected}, 实际 {resp.status_code}\n{resp.text}"
        )

        # DB 校验：创建成功
        if case.get("db_check") and expected == 201:
            cid = resp.json()["id"]
            rows = db.query("SELECT * FROM comments WHERE id = ?", (cid,))
            assert len(rows) == 1, "评论未落库"
            assert rows[0]["article_id"] == article_id
            assert rows[0]["user_id"] == db.get_user_by_username(
                logged_in_user["username"]
            )["id"]

        # 列表校验
        if case.get("expect_non_empty") and expected == 200:
            assert len(resp.json()) > 0
        if case.get("expect_empty") and expected == 200:
            assert len(resp.json()) == 0