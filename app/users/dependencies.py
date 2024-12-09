from fastapi import Request
from app.exceptions import TokenExpiredException, NoJwtException
from app.exceptions import NoUserIdException, TokenNoFoundException
import jwt
from app.config import get_auth_data
from app.users.dao import UsersDAO


class Auth:
    def __init__(self, request: Request):
        # Получение токена из запроса
        self.request = request
        self.token = self.get_token()

    def get_token(self):
        # Получение токена из куки 'access_token'
        token = self.request.cookies.get('access_token')
        if not token:
            raise TokenNoFoundException
        return token

    async def get_current_user(self):
        # Декодирование токена и получение информации о пользователе
        try:
            auth_data = get_auth_data()
            payload = jwt.decode(
                self.token, auth_data['secret_key'],
                algorithms=[auth_data['algorithm']]
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpiredException
        except jwt.InvalidTokenError:
            raise NoJwtException

        user_id = payload.get('sub')
        if not user_id:
            raise NoUserIdException

        user = await UsersDAO.find_one_or_none(user_id)
        if not user:
            raise NoUserIdException

        return user

    async def check_authenticated_user(self):
        # Проверка аутентификации
        return await self.get_current_user()


async def auth_dependency(request: Request):
    # Вызов зависимости для получения текущего пользователя
    auth = Auth(request)
    return await auth.check_authenticated_user()
