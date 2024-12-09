from datetime import datetime
from typing import List
from sqlalchemy import Integer, Text, ForeignKey, String, Table, Column, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship, Relationship
from app.chat.schemas import MessageStatus
from app.database import Base


class Message(Base):
    """
    Класс для модели сообщения
    """
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"))
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    recipient_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[MessageStatus] = mapped_column(String, default=MessageStatus.SENT)
    read_by: Mapped[List[int]] = mapped_column(String, default=[])
    edited_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_file: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    files: Mapped[List["File"]] = relationship("File", back_populates="message", lazy="selectin")


# Ассоциативная таблица для связи между User и Chat
chat_user_association = Table(
    "chat_user_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("chat_id", Integer, ForeignKey("chats.id"), primary_key=True),
)


class Chat(Base):
    """
    Класс для модели чата
    """
    __tablename__ = 'chats'
    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    files: Mapped[List["File"]] = relationship("File", back_populates = "chat")
    # Двусторонняя связь с User
    participants = Relationship("User", secondary=chat_user_association,
                                back_populates="chats", lazy="selectin")


class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    message_id = Column(Integer, ForeignKey("messages.id"))
    message = relationship("Message", back_populates="files")
    chat_id = Column(Integer, ForeignKey("chats.id"))
    chat = relationship("Chat", back_populates="files")

    def __init__(self, filename: str, file_path: str, chat_id: int, message_id: int = None):
        super().__init__()
        self.filename = filename
        self.file_path = file_path
        self.chat_id = chat_id
        self.message_id = message_id
