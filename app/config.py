import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


# Настройки конфигурации
class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str
    GITLAB_CLIENT_ID: str
    GITLAB_CLIENT_SECRET: str
    REDIRECT_URI: str
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    )


settings = Settings()


def get_auth_data():
    return {"secret_key": settings.SECRET_KEY, "algorithm": settings.ALGORITHM}