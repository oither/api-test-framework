import uuid
import allure
import pytest
from utils.data_loader import parametrize_from_yaml, resolve_placeholders


@allure.epic("博客系统API测试")
@allure.feature("认证模块")
class TestAuth:

    @allure.story("用户注册与登录")
    @allure.title("{case[title]}")
    @parametrize_from_yaml("auth_data.yaml")
    def test_auth_scenarios(self, auth_api, db, registered_user, disabled_user, case):
        case = resolve_placeholders(case)
        action = case["action"]
        expected = case["expected_status"]

        if action == "register":
            resp = auth_api.register(
                username=case.get("username"),
                email=case.get("email"),
                password=case.get("password"),
            )

        elif action == "register_duplicate_username":
            # 先注册一个用户，再用相同用户名注册
            uid = uuid.uuid4().hex[:6]
            auth_api.register(f"dup_{uid}", f"dup_{uid}@example.com", "Test@123456")
            resp = auth_api.register(f"dup_{uid}", f"other_{uid}@example.com", "Test@123456")
            # 清理第一个用户
            db.query("DELETE FROM users WHERE username = ?", (f"dup_{uid}",))

        elif action == "register_duplicate_email":
            uid = uuid.uuid4().hex[:6]
            auth_api.register(f"dup_e_{uid}", f"dup_email_{uid}@example.com", "Test@123456")
            resp = auth_api.register(f"other_{uid}", f"dup_email_{uid}@example.com", "Test@123456")
            db.query("DELETE FROM users WHERE username = ?", (f"dup_e_{uid}",))

        elif action == "login":
            username = case.get("username_override", registered_user["username"])
            password = case.get("password_override", registered_user["password"])
            resp = auth_api.login(username, password)

        elif action == "login_form":
            username = case.get("username_override", registered_user["username"])
            password = case.get("password_override", registered_user["password"])
            resp = auth_api.login_form(username, password)

        elif action == "login_disabled":
            resp = auth_api.login(disabled_user["username"], disabled_user["password"])

        else:
            pytest.fail(f"未知的 action: {action}")

        # ===== 断言 1：状态码 =====
        assert resp.status_code == expected, (
            f"[{case['title']}] 期望 {expected}, 实际 {resp.status_code}\n响应: {resp.text}"
        )

        # ===== 断言 2：DB 校验（仅注册成功场景）=====
        if case.get("db_check") and expected == 201:
            user = db.get_user_by_username(case["username"])
            assert user is not None, "注册成功但 DB 无记录"
            assert user["hashed_password"] != case["password"], "密码未加密"
            assert user["is_active"] == 1, "新用户应默认激活"

        # ===== 断言 3：Token 可用性（仅登录成功场景）=====
        if case.get("check_token") and expected == 200:
            data = resp.json()
            assert "access_token" in data, "响应缺少 access_token"
            assert data["token_type"] == "bearer"
            # 用"需要鉴权且无副作用"的请求验证 Token 真实有效：
            # GET /articles 是公开接口不能用来验证；PUT 不存在文章，
            # 有效 Token 通过鉴权层后返回 404，无效 Token 被拦截返回 401
            auth_api.set_token(data["access_token"])
            verify = auth_api.request("PUT", "/articles/999999", json={"title": "x"})
            assert verify.status_code == 404, (
                f"Token 未通过鉴权校验: 期望 404(资源不存在), 实际 {verify.status_code}"
            )
            auth_api.set_token(None)  # 还原，避免污染其他用例

    @allure.story("权限校验")
    @allure.title("未携带Token访问受保护接口 → 401")
    @pytest.mark.parametrize("method,path", [
        ("POST", "/articles"),
        ("PUT", "/articles/1"),
        ("DELETE", "/articles/1"),
        ("POST", "/articles/1/comments"),
        ("DELETE", "/articles/1/comments/1"),
    ], ids=[
        "创建文章-无Token",
        "更新文章-无Token",
        "删除文章-无Token",
        "创建评论-无Token",
        "删除评论-无Token",
    ])
    def test_unauthorized_access(self, auth_api, method, path):
        auth_api.set_token(None)
        resp = auth_api.request(method, path)
        assert resp.status_code == 401

    @allure.story("权限校验")
    @allure.title("携带无效Token → 401")
    def test_invalid_token(self, auth_api):
        auth_api.set_token("invalid.token.string")
        resp = auth_api.get("/articles")
        # 列表接口不需要鉴权，换一个需要鉴权的
        resp = auth_api.request("POST", "/articles", json={"title": "t", "content": "c"})
        assert resp.status_code == 401
        auth_api.set_token(None)

    @allure.story("权限校验")
    @allure.title("校验顺序：无Token + 不存在资源 → 401（非404）")
    def test_auth_before_not_found(self, auth_api):
        """验证 README 中标注的 401→404→403 校验顺序"""
        auth_api.set_token(None)
        resp = auth_api.request("PUT", "/articles/999999", json={"title": "x"})
        assert resp.status_code == 401, "应先校验鉴权(401)，而非资源存在性(404)"