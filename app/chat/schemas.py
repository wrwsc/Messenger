from typing import List

from fastapi import UploadFile
from pydantic import BaseModel, Field
from enum import Enum


# Схемы Pydantic для валидации и сериализации данных чата
class MessageStatus(str, Enum):
    SENT = "отправлено"
    DELIVERED = "доставлено"
    READ = "прочитано"


# Базовая схема для сообщений чата
class MessageBase(BaseModel):
    chat_id: int = Field(..., description="ID чата")
    sender_id: int = Field(..., description="ID отправителя сообщения")
    content: str = Field(..., description="Содержимое сообщения")
    status: MessageStatus = Field(default=MessageStatus.SENT,
                                  description="Статус сообщения")


class MessageRead(MessageBase):
    id: int = Field(..., description="Уникальный идентификатор сообщения")
    recipient_id: int = Field(..., description="ID получателя сообщения")
    read_by: List[int] = []

    class Config:
        from_attributes = True


class MessageCreate(MessageBase):
    sender_id: int = Field(..., description="ID отправителя сообщения")
    recipient_id: int = Field(..., description="ID получателя сообщения")
    files: List[UploadFile] = []


class ChatCreate(BaseModel):
    name: str = Field(..., description="Имя чата")
    participant_ids: List[int] = Field(..., description="ID участников чата")


class ChatBase(BaseModel):
    name: str = Field(..., description="Имя чата")


class ChatRead(ChatBase):
    id: int = Field(..., description="ID чата")
    participant_ids: List[int] = Field(
        default=[], 
        description="ID участников чата"
    )


class FileBase(BaseModel):
    filename: str = Field(..., description="Имя файла")
    file_path: str = Field(..., description="Путь файла")


class FileCreate(FileBase):
    chat_id: int = Field(..., description="ID чата")


class FileRead(BaseModel):
    id: int
    filename: str
    file_path: str
    chat_id: int

    class Config:
        from_attributes = True