from api.base_api import BaseAPI


class ArticleAPI(BaseAPI):
    def create(self, title: str, content: str):
        return self.post("/articles", json={"title": title, "content": content})

    def list(self, skip: int = 0, limit: int = 10, search: str = None):
        params = {"skip": skip, "limit": limit}
        if search:
            params["search"] = search
        return self.get("/articles", params=params)

    def detail(self, article_id: int):
        return self.get(f"/articles/{article_id}")

    def update(self, article_id: int, **fields):
        return self.put(f"/articles/{article_id}", json=fields)

    def delete_article(self, article_id: int):
        return self.delete(f"/articles/{article_id}")