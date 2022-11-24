from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .base import Base


class Article(Base):
    __tablename__ = "articles"

    _id = Column(Integer, primary_key=True)

    wallapop_id = Column(String, nullable=True)
    url = Column(String, nullable=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)

    user_articles = relationship("UserArticle", back_populates="article")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted = Column(Integer, server_default="0")

    UniqueConstraint(wallapop_id, name="u_wallapop_id")
