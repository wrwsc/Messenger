from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.chat.models import chat_user_association
from app.database import Base
from pydantic import EmailStr


class User(Base):
    __tablename__ = 'users'
    # Будет хранить ники пользователей, без нулевых элементов
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[EmailStr] = mapped_column(String, unique=True, index=True)
    chats = relationship(
        "Chat", secondary=chat_user_association, 
        back_populates="participants"
    )