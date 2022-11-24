from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .base import Base


class UserArticle(Base):
    __tablename__ = "user_articles"

    _id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users._id"), nullable=False)
    user = relationship("User", back_populates="user_articles", uselist=False)

    article_id = Column(Integer, ForeignKey("articles._id"), nullable=False)
    article = relationship("Article", back_populates="user_articles", uselist=False)

    notified = Column(Integer, server_default="0")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted = Column(Integer, server_default="0")

    UniqueConstraint(user_id, article_id, name="u_user_id_article_id")
