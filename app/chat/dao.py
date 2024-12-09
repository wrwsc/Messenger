import os
from datetime import datetime
from fastapi import HTTPException, UploadFile, File
from app.chat.schemas import MessageStatus
from app.dao.base import BaseDAO
from app.chat.models import Message, Chat
from app.database import async_session_maker
from app.users.models import User
from sqlalchemy import select
from app.chat.models import File


class MessagesDAO(BaseDAO):
    """DAO для работы с сообщениями чата"""
    model = Message

    @classmethod
    async def get_messages_between_users(cls, chat_id: int):
        """
        Получение всех сообщений в определённом чате
        :param chat_id: ID чата
        :return: Список сообщений
        """
        async with async_session_maker() as session:
            query = (
                select(cls.model)
                .filter(cls.model.chat_id == chat_id)
                .order_by(cls.model.id)
            )
            result = await session.execute(query)
            messages = result.scalars().all()
            for message in messages:
                message.chat_id = chat_id

            return messages or []

    @classmethod
    async def add_message(cls, chat_id: int, sender_id: int, recipient_id: int, content: str,
                          status: str, read_by: str = '', is_file: bool = False):
        """
        Добавление сообщения в базу данных
        :param recipient_id:
        :param chat_id: ID чата
        :param sender_id: ID отправителя
        :param content: Содержание сообщения
        :param status: Статус сообщения
        :param read_by: ID пользователей, которые прочитали сообщение
        :param is_file: ...
        :return: Сообщение
        """
        async with async_session_maker() as session:
            async with session.begin():
                new_message = cls.model(
                    chat_id=chat_id,
                    sender_id=sender_id,
                    recipient_id = recipient_id,
                    content=content,
                    status=status,
                    read_by=read_by,
                    is_file = is_file
                )
                session.add(new_message)
                await session.commit()
                return new_message

    @classmethod
    async def mark_message_as_read(cls, message_id: int, user_id: int):
        """
        Отметка сообщения как прочитанное
        :param message_id: ID сообщения
        :param user_id: ID пользователя
        :return: Сообщение, если оно было найдено, иначе None
        """
        async with async_session_maker() as session:
            async with session.begin():
                message = await session.get(cls.model, message_id)
                if message:
                    read_by_ids = []
                    if message.read_by:
                        read_by_ids = message.read_by.split(",")
                    # Проверяем, не прочитал ли уже пользователь сообщение
                    if str(user_id) not in read_by_ids:
                        # добавляем пользователя в список прочитавших
                        read_by_ids.append(str(user_id))
                        # преобразуем обратно в строку
                        message.read_by = ",".join(read_by_ids)
                        await session.commit()
                    return message
                return None

    @classmethod
    async def delete_message(cls, message_id: int, user_id: int):
        async with async_session_maker() as session:
            async with session.begin():
                message = await session.get(Message, message_id)
                if not message:
                    raise HTTPException(status_code = 404, detail = "Сообщение не найдено")

                if message.sender_id != user_id:
                    raise HTTPException(status_code = 403, detail = "Невозможно удалить данное сообщение")
                await session.delete(message)
                await session.commit()
                return True

    @classmethod
    async def get_chat_id_for_message(cls, message_id: int):
        async with async_session_maker() as session:
            query = select(cls.model.chat_id).where(cls.model.id == message_id)
            result = await session.execute(query)
            if not result:
                raise HTTPException(status_code = 404, detail = "Не найден чат или сообщение")
            chat_id = result.scalar()
            return chat_id

    @classmethod
    async def get_message_by_id(cls, message_id: int):
        async with async_session_maker() as session:
            message = await session.get(cls.model, message_id)
            return message

    @classmethod
    async def update_message(cls, message_id: int, new_content: str):
        async with async_session_maker() as session:
            async with session.begin():
                message = await session.get(cls.model, message_id)
                if message:
                    message.content = new_content
                    message.edited_at = datetime.utcnow()
                    await session.commit()
                    return message
                raise HTTPException(status_code=404, detail="Сообщение не найдено")

    @classmethod
    async def forward_message(cls, original_message: Message, target_chat_id: int, sender_id: int):
        async with async_session_maker() as session:
            async with session.begin():
                forwarded_message = cls.model(
                    chat_id = target_chat_id,
                    sender_id = sender_id,
                    recipient_id = None,
                    content = original_message.content,
                    status = MessageStatus.SENT
                )
                session.add(forwarded_message)
                await session.commit()
                return forwarded_message


class ChatDAO:
    @staticmethod
    async def create_chat(name: str, participant_ids: list[int]):
        """
        Создание чата
        :param name: Название чата
        :param participant_ids: ID пользователей, которые входят в чат
        :return: Новый чат
        """
        async with async_session_maker() as session:
            async with session.begin():
                new_chat = Chat(name=name)
                for participant_id in participant_ids:
                    user = await session.get(User, participant_id)
                    if user:
                        new_chat.participants.append(user)
                session.add(new_chat)
                await session.flush()
                await session.commit()
                return new_chat

    @classmethod
    async def get_chat(cls, chat_id):
        """
        Получение информации о чате и его сообщениях
        :param chat_id: ID чата
        :return: Список сообщений
        """
        async with async_session_maker() as session:
            chat = await session.get(Chat, chat_id)
            if chat is None:
                raise HTTPException(status_code=404, detail="Chat not found")
            messages = await MessagesDAO.get_messages_between_users(chat_id)
            return {
                "chat": chat,
                "messages": messages,
            }

    @classmethod
    async def get_or_create_chat_between_users(cls, user1_id: int, user2_id: int):
        """
        Получить чат между двумя пользователями или создать его, если он не существует.
        :param user1_id: ID первого пользователя
        :param user2_id: ID второго пользователя
        :return: Объект чата
        """
        async with async_session_maker() as session:
            # Ищем чат между двумя конкретными пользователями
            chat_query = await session.execute(
                select(Chat)
                .filter(Chat.participants.any(User.id == user1_id))
                .filter(Chat.participants.any(User.id == user2_id))
            )

            chats = chat_query.scalars().all()
            # Если чат существует, возвращаем его
            if chats:
                return chats[0]

            # Если чата нет, создаём новый чат
            new_chat = await cls.create_chat(
                name = f"Чат между {user1_id} и {user2_id}",
                participant_ids = [user1_id, user2_id]
            )
            return new_chat

    @staticmethod
    async def get_chats_for_user(user_id: int):
        async with async_session_maker() as session:
            result = await session.execute(
                select(Chat)
                .join(Chat.participants)
                .where(Chat.participants.any(User.id == user_id))
            )
            chats = result.scalars().all()
            chat_data = []
            setter_chats = set()

            for chat in chats:
                if chat.id in setter_chats:
                    continue
                setter_chats.add(chat.id)

                other_users = [user for user in chat.participants if user.id != user_id]
                name = other_users[0].name if len(other_users) == 1 else chat.name

                # Получаем последнее сообщение для чата
                last_message = await ChatDAO.get_last_message_for_chat(chat.id)
                last_message_content = last_message.content if last_message else "Нет сообщений"

                chat_data.append({
                    "id": chat.id,
                    "name": name,
                    "last_message_content": last_message_content,
                })

            return chat_data

    @staticmethod
    async def get_last_message_for_chat(chat_id: int):
        """
        Получение последнего сообщения для чата.
        :param chat_id: ID чата
        :return: Последнее сообщение или None
        """
        async with async_session_maker() as session:
            query = select(Message).filter(Message.chat_id == chat_id).order_by(Message.id.desc())
            result = await session.execute(query)
            last_message = result.scalars().first()
            return last_message


class FilesDAO:

    @staticmethod
    async def save_file(file: UploadFile, chat_id: int, session: async_session_maker):
        file_location = f"uploads/{file.filename}"
        with open(file_location, "wb") as f:
            f.write(await file.read())
        new_file = File(filename = file.filename, file_path = file_location, chat_id = chat_id)
        session.add(new_file)
        await session.commit()
        return new_file