import json
from app.chat.models import Chat
from app.chat.schemas import MessageCreate, MessageRead, ChatRead, ChatCreate, MessageStatus, FileRead
from app.database import async_session_maker
from app.users.dependencies import auth_dependency
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict
from app.chat.dao import MessagesDAO, ChatDAO, FilesDAO
from app.users.dao import UsersDAO
from app.users.models import User
import asyncio

router = APIRouter(prefix="/bittalk-mes", tags=["bittalk"])
active_connections: Dict[int, List[WebSocket]] = {}


@router.get("/", response_class=JSONResponse, summary="Получение списка чатов")
async def get_chats(current_user = Depends(auth_dependency)):
    try:
        chats = await ChatDAO.get_chats_for_user(user_id=current_user.id)
        return chats
    except Exception as e:
        print(f"Error fetching chats: {str(e)}")
        raise HTTPException(status_code=500, detail="Server error")


@router.post("/messages/", response_model=MessageRead,
             summary="Отправка сообщения в чате")
async def send_message(message_create: MessageCreate,
                       current_user: User = Depends(auth_dependency)):
    """
    Отправка сообщения в чате
    :param message_create: Данные для создания сообщения
    :param current_user: Аутентифицированный пользователь
    :return: Сохраненное сообщение
    :raises HTTPException: Если чат не найден или другие ошибки
    """
    chat_id = message_create.chat_id
    file_entity = None

    if message_create.files:
        file = message_create.files[0]
        file_entity = await FilesDAO.save_file(file, chat_id = chat_id)

    if chat_id:
        # Если chat_id передан, пытаемся найти чат с этим chat_id
        chat = await ChatDAO.get_chat(chat_id)
        if not chat:
            raise HTTPException(status_code = 404, detail = "Chat not found")
    else:
        # Если chat_id не передан, пытаемся создать новый чат
        chat = await ChatDAO.get_or_create_chat_between_users(current_user.id, message_create.recipient_id)
        if not chat:
            raise HTTPException(status_code = 500, detail = "Ошибка при создании чата")
        chat_id = chat.id


    read_by = json.dumps([])  # по умолчанию список тех, кто прочитал сообщение, пустой
    message = await MessagesDAO.add_message(
        chat_id = chat_id,
        sender_id = message_create.sender_id,
        recipient_id = message_create.recipient_id,
        content = message_create.content,
        status = message_create.status,
        read_by = read_by,
        is_file = bool(file_entity)
    )

    message_read = MessageRead(
        id = message.id,
        chat_id = message.chat_id,
        sender_id = message.sender_id,
        recipient_id = message.recipient_id,
        content = message.content,
        status = message.status,
        files = [file_entity] if file_entity else []
    )

    await notify_user(chat_id, {
        "action": "new_message",
        "message": message_read.dict()
    })
    print(
        f"Sending message: sender_id={current_user.id}, recipient_id={message_create.recipient_id}, chat_id={chat_id}")
    return message_read


async def notify_user(chat_id: int, message: dict):
    """
    Уведомление пользователей о новом сообщении в чате.
    :param chat_id: Идентификатор чата
    :param message: Сообщение для уведомления
    """
    message["chat_id"] = chat_id
    for connection in active_connections.get(chat_id, []):
        await connection.send_json(message)


@router.websocket("/ws/{chat_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, user_id: int):
    """
    Функция обработки вебсокет-соединения.
    :param websocket: Вебсокет-соединение
    :param chat_id: Идентификатор чата
    :param user_id: Идентификатор пользователя
    :raises WebSocketDisconnect: Если соединение прервано
    """
    await websocket.accept()

    if chat_id not in active_connections:
        active_connections[chat_id] = []

    active_connections[chat_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data["action"] == "new_message":
                data["message"]["chat_id"] = chat_id
                await notify_user(chat_id, {
                    "action": "new_message",
                    "message": data["message"]
                })
            elif data["action"] == "new_file":
                await notify_user(chat_id, {
                    "action": "new_file",
                    "message": data["message"]
                })

            elif data["action"] == "forward_message":
                original_message_id = data["message_id"]
                target_chat_id = data["target_chat_id"]

                # Пересылка сообщения
                original_message = await MessagesDAO.get_message_by_id(original_message_id)
                if not original_message:
                    raise HTTPException(status_code=404, detail="Message not found")

                # Пересылаем сообщение в целевой чат
                forwarded_message = await MessagesDAO.add_message(
                    chat_id=target_chat_id,
                    sender_id=user_id,
                    recipient_id=original_message.recipient_id,  # Можно изменить на нужного получателя
                    content=original_message.content,
                    status=MessageStatus.SENT
                )

                # Уведомление участников целевого чата
                await notify_user(target_chat_id, {
                    "action": "new_message",
                    "message": {
                        "id": forwarded_message.id,
                        "chat_id": forwarded_message.chat_id,
                        "sender_id": forwarded_message.sender_id,
                        "content": forwarded_message.content,
                        "status": forwarded_message.status
                    }
                })

            # Логика для обработки прочтения сообщения
            elif data["action"] == "read_message":
                await MessagesDAO.mark_message_as_read(
                    data["message_id"],
                    user_id
                )
                await notify_user(chat_id, {
                    "action": "message_read",
                    "message_id": data["message_id"],
                    "read_by": user_id,
                    "chat_id": chat_id
                })

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        active_connections[chat_id].remove(websocket)
        if not active_connections[chat_id]:
            del active_connections[chat_id]


@router.get("/messages/{chat_id}", response_model=List[MessageRead],
            summary = "Получение сообщений в чате")
async def get_messages(chat_id: int,
                       current_user: User = Depends(auth_dependency)):
    """
    Получение списка сообщений в определённом чате
    :param chat_id: Идентификатор чата
    :param current_user: Аутентифицированный пользователь
    :return: Список сообщений в чате
    """
    messages = await MessagesDAO.get_messages_between_users(chat_id=chat_id)
    return [
        MessageRead(
            id=message.id,
            chat_id=message.chat_id,
            sender_id=message.sender_id,
            content=message.content,
            status=message.status,
            recipient_id=current_user.id,
            files = message.files,
        )
        for message in messages
    ]


@router.get("/chat/{chat_id}", summary="Получить чат между пользователями")
async def get_chat(chat_id: int, current_user: User = Depends(auth_dependency)):
    """
    Получение информации о чате и его сообщениях, если пользователь является участником чата.
    :param chat_id: Идентификатор чата
    :param current_user: Аутентифицированный пользователь
    :return: Информация о чате и его сообщениях
    """
    async with async_session_maker() as session:
        # Получаем чат из базы данных
        chat = await session.get(Chat, chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        # Проверяем, является ли текущий пользователь участником чата
        if current_user.id not in [participant.id for participant in chat.participants]:
            raise HTTPException(status_code=403, detail="Access denied to this chat")

        # Получаем сообщения чата
        messages = await MessagesDAO.get_messages_between_users(chat_id)

        return {
            "chat": chat,
            "messages": messages,
        }


@router.post("/messages/{message_id}/read",
             summary="Отметить сообщение как прочитанное")
async def read_message(message_id: int,
                       current_user: User = Depends(auth_dependency)):
    """
    Отметить сообщение как прочитанное
    :param message_id: Идентификатор сообщения
    :param current_user: Аутентифицированный пользователь
    :return: Сообщение об изменении статуса
    """
    message = await MessagesDAO.mark_message_as_read(
        message_id,
        current_user.id
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return {
        "message": "Сообщение изменило статус на прочитанное",
        "message_id": message_id
    }


@router.post("/chat/", response_model=ChatRead,
             summary='Создание группового чата')
async def create_chat(chat: ChatCreate):
    """
    Создание группового чата
    :param chat: Создание чата
    :return: Новый чат
    """
    new_chat = await ChatDAO.create_chat(
        name=chat.name,
        participant_ids=chat.participant_ids
    )
    return new_chat


@router.get("/current_user")
async def get_current_user_endpoint(current_user: User = Depends(auth_dependency)):
    """
    Получение информации о текущем аутентифицированном пользователе
    :param current_user: Аутентифицированный пользователь
    :return: Информация о текущем пользователе
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return {"user": current_user}


@router.get("/files/{filename}", summary="Загрузка файла")
async def download_file(filename: str):
    """
    Загрузка файла по имени
    :param filename: Имя файла
    :return: Файл
    """
    file_location = f"uploads/{filename}"
    return FileResponse(file_location)


@router.post("/messages/file/", response_model=FileRead, summary="Отправка файла")
async def send_file(
        chat_id: int,
        recipient_id: int,
        file: UploadFile = File(...),
        current_user: User = Depends(auth_dependency),
):
    async with async_session_maker() as session:
        chat = await ChatDAO.get_or_create_chat_between_users(current_user.id, recipient_id)
        message = await MessagesDAO.add_message(
            chat_id=chat.id,
            sender_id=current_user.id,
            recipient_id=recipient_id,
            content='',
            status=MessageStatus.SENT,
            is_file=True
        )
        file_entity = await FilesDAO.save_file(file, chat_id=chat.id, session=session)
        message_dict = {
            "id": message.id,
            "chat_id": message.chat_id,
            "sender_id": message.sender_id,
            "recipient_id": message.recipient_id,
            "content": message.content,
            "status": message.status,
            "files": [file_entity]
        }
        message_read = MessageRead(**message_dict)
        await notify_user(chat.id, {"action": "new_message", "message": message_read.dict()})
        return FileRead(
            id=file_entity.id,
            filename=file_entity.filename,
            file_path=file_entity.file_path,
            chat_id=chat.id
        )


@router.delete("/messages/{message_id}", summary="Удаление сообщения")
async def delete_message(message_id: int, current_user: User = Depends(auth_dependency)):
    message = await MessagesDAO.delete_message(message_id, current_user.id)
    if message:
        chat_id = await MessagesDAO.get_chat_id_for_message(message_id)
        await notify_user(chat_id, {
            "action": "delete_message",
            "message_id": message_id
        })
        return {"message": "Сообщение успешно удалено"}


@router.put("/messages/{message_id}/edit", response_model = MessageRead, summary = "Редактирование сообщения")
async def edit_message(message_id: int, message_create: MessageCreate, current_user: User = Depends(auth_dependency)):
    message = await MessagesDAO.get_message_by_id(message_id)
    if not message:
        raise HTTPException(status_code = 404, detail = "Сообщение не найдено")
    if message.sender_id != current_user.id:
        raise HTTPException(status_code = 403, detail = "Вы не можете редактировать это сообщение")
    updated_message = await MessagesDAO.update_message(message_id, message_create.content)
    chat_id = updated_message.chat_id
    message_read = MessageRead(
        id = updated_message.id,
        chat_id = updated_message.chat_id,
        sender_id = updated_message.sender_id,
        recipient_id = updated_message.recipient_id,
        content = updated_message.content,
        status = updated_message.status,
    )

    await notify_user(chat_id, {
        "action": "edit_message",
        "message": message_read.dict()
    })
    return message_read


@router.post("/messages/{message_id}/forward", summary="Пересылка сообщения")
async def forward_message(
    message_id: int,
    target_chat_id: int,
    current_user: User = Depends(auth_dependency)
):
    original_message = await MessagesDAO.get_message_by_id(message_id)
    if not original_message:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    if current_user.id not in [original_message.sender_id, original_message.recipient_id]:
        raise HTTPException(status_code=403, detail="Вы не можете пересылать это сообщение")
    forwarded_message = await MessagesDAO.add_message(
        chat_id=target_chat_id,
        sender_id=current_user.id,
        recipient_id=original_message.recipient_id,
        content=original_message.content,
        status=MessageStatus.SENT
    )
    await notify_user(target_chat_id, {
        "action": "new_message",
        "message": {
            "id": forwarded_message.id,
            "chat_id": forwarded_message.chat_id,
            "sender_id": forwarded_message.sender_id,
            "content": forwarded_message.content,
            "status": forwarded_message.status
        }
    })

    return {"message": "Сообщение успешно переслано", "forwarded_message_id": forwarded_message.id}


@router.get("/chat-between/{user1_id}/{user2_id}", summary = "Получить или создать чат между пользователями")
async def get_or_create_chat_between_users(user1_id: int, user2_id: int, current_user: User = Depends(auth_dependency)):
    if current_user.id not in [user1_id, user2_id]:
        raise HTTPException(status_code = 403, detail = "Access denied to this operation")

    chat = await ChatDAO.get_or_create_chat_between_users(user1_id, user2_id)
    return {"id": chat.id}
