from fastapi import APIRouter, Response, Depends, HTTPException, Request, Query
import requests
from app.config import settings
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.users.auth import create_access_token
from app.users.auth import authenticate_user_in_gitlab
from app.users.dao import UsersDAO
from app.users.dependencies import auth_dependency
from app.users.models import User
from app.users.schemas import UserRead
from typing import List
from fastapi.templating import Jinja2Templates

# Создание API-маршрута для авторизации пользователя
router = APIRouter(prefix='/auth', tags=['Auth'])


@router.get('/login')
async def login_in_gitlab(code: str, response: Response):
    """
    Авторизация пользователя в GitLab
    :param code: Код авторизации из GitLab
    :param response: Ответ сервера
    :return: Редирект на страницу авторизации BitTalk-Mes
    """
    token = await authenticate_user_in_gitlab(code)
    if not token:
        raise HTTPException(status_code=400, detail='Неверный код авторизации')

    # Получение информации о пользователе
    user_info_url = "https://git.66bit.ru/api/v4/user"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    user_response = requests.get(user_info_url, headers=headers)

    if user_response.status_code != 200:
        raise HTTPException(
            status_code=user_response.status_code,
            detail=user_response.json()
        )

    user_info = user_response.json()
    user = await UsersDAO.find_one_or_none(email=user_info['email'])

    # Регистрация пользователя, если он не существует
    if not user:
        user = await UsersDAO.add(
            name=user_info['name'],
            email=user_info['email'],
        )

    if not user:
        raise HTTPException(
            status_code=500,
            detail="Не удалось создать пользователя"
        )

    # Создание токенов
    access_token = create_access_token(data={"sub": user.email})
    response = RedirectResponse(url = "http://localhost:5173/bittalk-mes/")
    response.set_cookie(key="access_token", value=access_token,
                        secure=True, samesite="Lax")
    # Установка токенов в cookies и перенаправление пользователя
    return response


@router.post('/logout')
async def logout_user(response: Response):
    """
    Выход пользователя из аккаунта
    :param response: Ответ сервера
    :return: Сообщение об успешном выходе
    """
    response.delete_cookie(key='access_token')
    return {'message': 'Пользователь вышел из аккаунта'}


@router.get("/search", summary="Поиск пользователей")
async def search_users(query: str, current_user: User = Depends(auth_dependency)):
    if not query:
        return []
    users = await UsersDAO.search_users(query=query)
    return [{"id": user.id, "name": user.name} for user in users if user.id != current_user.id]

