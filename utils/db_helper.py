import sqlite3
from pathlib import Path
from config.settings import get_settings
from utils.logger import logger

class DBHelper:
    def __init__(self):
        self.db_path = get_settings().db_path
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = sqlite3.connect(self.db_path, timeout=10)  # ← 加 timeout
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, params)
        conn.commit()  # ← 加 commit，支持 UPDATE/DELETE
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        logger.debug(f"DB: {sql} | params={params} | rows={len(results)}")
        return results

    def get_user_by_username(self, username: str) -> dict | None:
        rows = self.query("SELECT * FROM users WHERE username = ?", (username,))
        return rows[0] if rows else None

    def get_article(self, article_id: int) -> dict | None:
        rows = self.query("SELECT * FROM articles WHERE id = ?", (article_id,))
        return rows[0] if rows else None

    def count_comments(self, article_id: int) -> int:
        rows = self.query("SELECT COUNT(*) as cnt FROM comments WHERE article_id = ?", (article_id,))
        return rows[0]["cnt"] if rows else 0