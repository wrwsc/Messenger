from app.database import async_session_maker
from app.users.models import User
from sqlalchemy.future import select


class UsersDAO:
    model = User

    @staticmethod
    async def find_one_or_none(email: str):
        """
        Ищет пользователя в бд по email
        :param email: адрес электронной почты
        :return: пользователь или None, если такой пользователь не найден
         """
        async with async_session_maker() as session:
            result = await session.execute(select(User).filter_by(email=email))
            return result.scalar_one_or_none()

    @staticmethod
    async def add(name: str, email: str):
        """
        Добавляет нового пользователя в бд
        :param name: имя пользователя
        :param email: адрес электронной почты
        :return: добавленный пользователь
        """
        user = User(name=name, email=email)
        async with async_session_maker() as s:
            s.add(user)
            await s.commit()
            # Обновление объекта, чтобы получить все поля, включая ID
            await s.refresh(user)
        return user

    @classmethod
    async def find_all(cls):
        """
        Возвращает всех пользователей из бд
        :return: список пользователей
        """
        async with async_session_maker() as session:
            query = select(cls.model)
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def search_users(cls, query: str):
        """
        Ищет пользователей в бд по имени
        :param query: искомое имя
        :return: список пользователей
        """
        async with async_session_maker() as session:
            search_query = f"%{query}%"
            result = await session.execute(
                select(cls.model)
                .filter(cls.model.name.ilike(search_query))
            )
            return result.scalars().all()