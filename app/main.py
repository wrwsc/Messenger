from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.exceptions import TokenExpiredException, TokenNoFoundException
from app.users.router import router as users_router
from app.chat.router import router as chat_router

app = FastAPI()

origins = [
    'http://localhost:8000',
    'http://1270.0.0.1:8000'
]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить запросы с любых источников.
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)

# Маршруты
app.include_router(users_router)
app.include_router(chat_router)


@app.get("/")
# Перенаправление на страницу авторизации
async def redirect_to_auth():
    return RedirectResponse(url="http://localhost:5173/auth")


@app.exception_handler(TokenExpiredException)
# Обработчик исключений
async def token_expired_exception_handler(request: Request,
                                          exc: HTTPException):
    print(f"Token expired: {exc.detail}")
    return RedirectResponse(url="http://localhost:5173/auth")


@app.exception_handler(TokenNoFoundException)
# Обработчик исключений
async def token_no_found_exception_handler(request: Request,
                                           exc: HTTPException):
    # Возвращаем редирект на страницу /auth
    print(f"Token not found: {exc.detail}")
    return RedirectResponse(url="http://localhost:5173/auth")