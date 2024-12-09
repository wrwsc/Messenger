from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2AuthorizationCodeBearer
import jwt
from app.config import get_auth_data, settings
import requests

# Создание объекта pwd_context для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Создание объекта для реализации авторизации через OAuth 2.0
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://git.66bit.ru/oauth/authorize",
    tokenUrl="https://git.66bit.ru/oauth/token"
)

# Идентификатор и секретный ключ для авторизации пользователя в GitLab API
GITLAB_CLIENT_ID = settings.GITLAB_CLIENT_ID
GITLAB_CLIENT_SECRET = settings.GITLAB_CLIENT_SECRET


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Создаёт токен доступа
    :param data: Данные для создания токена
    :param expires_delta: Время жизни токена (по умолчанию 1 час)
    :return: Токен доступа
     """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode.update({"exp": expire})
    auth_data = get_auth_data()
    encode_jwt = jwt.encode(
        to_encode, auth_data['secret_key'],
        algorithm=auth_data['algorithm']
    )
    return encode_jwt


async def authenticate_user_in_gitlab(code: str):
    """
    Авторизация пользователя в GitLab и получение токенов
    :param code: Код авторизации
    :return: Токен доступа и токен обновления
     """
    token_url = "https://git.66bit.ru/oauth/token"
    data = {
        "client_id": GITLAB_CLIENT_ID,
        "client_secret": GITLAB_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:8000/auth/login"
    }
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        print("Ошибка авторизации:", response.status_code, response.text)
        return None
    return response.json().get("access_token")