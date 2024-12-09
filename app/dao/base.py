from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update, delete as sqlalchemy_delete
from app.database import async_session_maker


# Класс для доступа к данным, используемый в других модулях
class BaseDAO:
    model = None

    @classmethod
    async def find_one_or_none_by_id(cls, data_id: int):
        """
        Получает один экземпляр модели по идентификатору или None,
        если такой нет.
        :param data_id: Идентификатор экземпляра
        :return: Экземпляр модели или None
        """
        async with async_session_maker() as session:
            query = select(cls.model).filter_by(id=data_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    @classmethod
    async def find_one_or_none(cls, **filter_by):
        """
        Получает один экземпляр модели по указанным фильтрам или None,
        если такой нет.
        :param filter_by: Фильтры для выборки
        :return: Экземпляр модели или None
         """
        async with async_session_maker() as session:
            query = select(cls.model).filter_by(**filter_by)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    @classmethod
    async def add(cls, **values):
        """
        Добавляет новый экземпляр модели в базу данных
        :param values: Значения полей нового экземпляра
        :return: Новый экземпляр модели
        """
        async with async_session_maker() as session:
            async with session.begin():
                new_instance = cls.model(**values)
                session.add(new_instance)
                try:
                    await session.commit()
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e
                return new_instance

    @classmethod
    async def add_many(cls, instances: list[dict]):
        """
        Добавляет несколько новых экземпляров модели в базу данных
        :param instances: Список словарей с значениями полей новых экземпляров
        :return: Список новых экземпляров модели
        """
        async with async_session_maker() as session:
            async with session.begin():
                new_instances = [cls.model(**values) for values in instances]
                session.add_all(new_instances)
                try:
                    await session.commit()
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e
                return new_instances

    @classmethod
    async def update(cls, filter_by, **values):
        """
        Обновляет экземпляры модели в базе данных по указанным фильтрам
        :param filter_by: Фильтры для выборки
        :param values: Значения полей для обновления
        :return: Количество обнавленных экземпляров модели
        """
        async with async_session_maker() as session:
            async with session.begin():
                query = (
                    sqlalchemy_update(cls.model)
                    .where(*[getattr(cls.model, k) == v for k,
                           v in filter_by.items()])
                    .values(**values)
                    .execution_options(synchronize_session="fetch")
                )
                result = await session.execute(query)
                try:
                    await session.commit()
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e
                return result.rowcount

    @classmethod
    async def delete(cls, delete_all: bool = False, **filter_by):
        """
        Удаляет экземпляры модели в базе данных по указанным фильтрам
        :param delete_all: Удалять все экземпляры модели или нет
        :param filter_by: Фильтры для выборки
        :return: Количество удаленных экземпляров модели
        """
        if delete_all is False:
            if not filter_by:
                raise ValueError(
                    "Необходимо указать хотя бы один параметр для удаления."
                )

        async with async_session_maker() as session:
            async with session.begin():
                query = sqlalchemy_delete(cls.model).filter_by(**filter_by)
                result = await session.execute(query)
                try:
                    await session.commit()
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e
                return result.rowcount