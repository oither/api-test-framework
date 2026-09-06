from api.base_api import BaseAPI

class AuthAPI(BaseAPI):
    def register(self, username: str, email: str, password: str):
        return self.post("/auth/register", json={
            "username": username,
            "email": email,
            "password": password
        })

    def login(self, username: str, password: str):
        return self.post("/auth/login", json={
            "username": username,
            "password": password
        })
    
    def login_form(self, username: str, password: str):
        """Form Data 登录（Swagger 专用）"""
        return self.post("/auth/login/form", data={
            "username": username,
            "password": password
        })