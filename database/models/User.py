from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    _id = Column(Integer, primary_key=True)

    telegram_id = Column(Integer, nullable=False)
    search = Column(String, nullable=False)
    filter = Column(JSON, nullable=False)

    user_articles = relationship("UserArticle", back_populates="user")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted = Column(Integer, server_default="0")
