from api.base_api import BaseAPI


class CommentAPI(BaseAPI):
    def create(self, article_id: int, content: str):
        return self.post(
            f"/articles/{article_id}/comments",
            json={"content": content},
        )

    def list(self, article_id: int):
        return self.get(f"/articles/{article_id}/comments")

    def delete_comment(self, article_id: int, comment_id: int):
        return self.delete(f"/articles/{article_id}/comments/{comment_id}")