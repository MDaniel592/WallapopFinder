import logging

import utils.variables as variables
import wallabot
from utils.parse_number import parseNumber

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from database.models.Article import Article
from database.models.base import Session
from database.models.User import User
from database.models.UserArticle import UserArticle


def main():
    session = Session()
    users_articles = session.query(UserArticle).filter(UserArticle.notified == 0).all()

    counter = 0
    for user_article in users_articles:

        telegram_id = user_article.user.telegram_id
        article_url = user_article.article.url
        article_name = user_article.article.name
        article_description = user_article.article.description
        article_price = str(parseNumber(user_article.article.price)).replace(".", "\\.")

        for i in variables.SPECIAL_CHARS:
            article_name = article_name.replace(i, "\\" + str(i))
            article_description = article_description.replace(i, "\\" + str(i))

        msg = f"Nuevo artículo encontrado: [{article_name}]({article_url}) \n" + f"Precio: {article_price} \n" + f"Descripción: \n{article_description} \n"
        result = wallabot.send_user_alert(msg, telegram_id)
        if not result:
            logger.warning(f"NO se ha enviado correctamente el mensaje al usuario: {telegram_id}")
            continue

        session.query(UserArticle).filter(UserArticle._id == user_article._id).update({"notified": 1}, synchronize_session=False)
        counter += 1

    if counter > 0:
        session.commit()

    session.close()
