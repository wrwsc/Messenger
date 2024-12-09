from typing import Optional
from pydantic import BaseModel


# модель токена
class Token(BaseModel):
    access_token: str
    token_type: str


# модель данных токена
class TokenData(BaseModel):
    username: Optional[str] = None


# модель для поиска пользователей
class UserRead(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True