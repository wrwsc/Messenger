from sqlalchemy import func, Integer
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from dotenv import load_dotenv
import os

load_dotenv()

database_url = os.getenv('DATABASE_URL')
engine = create_async_engine(
    url=database_url,
    echo=True,
    pool_size = 10,  # Размер пула
    max_overflow = 10,  # Дополнительное количество соединений
    pool_timeout = 5  # Время ожидания для нового соединения
)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession,
                                         expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    # Определяем столбец id, который будет хранить в себе id пользователя
    # Столбец сделаем первичным ключом, и он будет увеличиваться автоматически
    #  с помощью автоинкремента ++
    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(),
                                                 onupdate=func.now())


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session