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
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, params)
        conn.commit()  # 支持 UPDATE/DELETE 等写操作
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

    def delete_user_data(self, username: str):
        """级联删除用户及其全部评论、文章（顺序符合外键指向：评论 → 文章 → 用户）"""
        self.query(
            "DELETE FROM comments WHERE user_id = (SELECT id FROM users WHERE username = ?)",
            (username,),
        )
        self.query(
            "DELETE FROM articles WHERE author_id = (SELECT id FROM users WHERE username = ?)",
            (username,),
        )
        self.query("DELETE FROM users WHERE username = ?", (username,))

    def delete_article_data(self, article_id: int):
        """删除文章及其评论。被测系统的 DELETE /articles 不级联删评论，
        fixture 清理时先删评论再删文章，避免留下孤儿评论记录"""
        self.query("DELETE FROM comments WHERE article_id = ?", (article_id,))
        self.query("DELETE FROM articles WHERE id = ?", (article_id,))
