import re
import uuid
import yaml
import pytest
from pathlib import Path
from faker import Faker

fake = Faker("zh_CN")
DATA_DIR = Path(__file__).parent.parent / "testdata"


def load_yaml(filename: str) -> list[dict]:
    """加载 YAML 测试数据"""
    filepath = DATA_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else data.get("cases", [])


def resolve_placeholders(data):
    """
    递归替换数据中的占位符：
      ${uuid}           → 8位随机hex
      ${random_username}→ 随机用户名
      ${random_email}   → 随机邮箱
    """
    if isinstance(data, str):
        data = data.replace("${uuid}", uuid.uuid4().hex[:8])
        data = data.replace("${random_username}", f"{fake.user_name()}_{uuid.uuid4().hex[:6]}")
        data = data.replace("${random_email}", f"{uuid.uuid4().hex[:8]}@example.com")
        return data
    elif isinstance(data, dict):
        return {k: resolve_placeholders(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_placeholders(item) for item in data]
    return data


def parametrize_from_yaml(filename: str):
    """装饰器：从 YAML 文件参数化用例，自动用 title 作为用例 ID"""
    cases = load_yaml(filename)
    ids = [c.get("title") or c.get("name") or f"case_{i}" for i, c in enumerate(cases)]
    return pytest.mark.parametrize("case", cases, ids=ids)


def generate_random_user() -> dict:
    """生成随机测试用户（用于 fixture 数据隔离）"""
    uid = uuid.uuid4().hex[:6]
    return {
        "username": f"testuser_{uid}",
        "email": f"testuser_{uid}@example.com",
        "password": "Test@123456",
    }