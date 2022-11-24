import asyncio
import datetime
import logging
import re

import aiohttp
import ujson

import utils.error_messages as error_messages
from database.models.Article import Article
from database.models.base import Session
from database.models.User import User
from database.models.UserArticle import UserArticle

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False

URL_BASE = (
    "https://api.wallapop.com/api/v3/general/search"
    + "?category_ids=14000"  # MOTOS
    + "&filters_source=quick_filters"
    + "&latitude=40.41956&longitude=-3.69196"
    + "&order_by=most_relevance"
)


WEB_ITEM = "https://es.wallapop.com/item/"

HEADERS = {
    "Host": "api.wallapop.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es,es-ES;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DeviceOS": "0",
    "X-DeviceOS": "0",
    "Origin": "https://es.wallapop.com",
    "DNT": " 1",
    "Connection": "keep-alive",
    "Referer": "https://es.wallapop.com/",
}


async def scrape_data(aiohttp_session, search_link, user_id, search, desired_words, min_price, max_price):

    logger.warning(f"OPENING: {search_link}")
    async with aiohttp_session.get(search_link, headers=HEADERS) as response:
        status_code = response.status
        if status_code != 200:
            return logger.warning(f"Status code is not 200: {status_code}")
        response = await response.text()

    response = ujson.loads(response)
    articles = response["search_objects"]

    current_time = datetime.datetime.now().replace(microsecond=0)
    articles_dict = {}
    db_session = Session()
    for article in articles:
        wallapop_id = article["id"]
        if not wallapop_id:
            logger.warning(error_messages.ID_NOT_FOUND)
            continue

        if articles_dict.get(wallapop_id, False):
            logger.warning(error_messages.REPEATED_PRODUCT_FOUND)
            continue

        product_link = article["web_slug"]
        if not product_link:
            logger.warning(error_messages.LINK_NOT_FOUND)
            continue

        product_link = WEB_ITEM + product_link

        product_name = article["title"]
        if not product_name:
            logger.warning(error_messages.NAME_NOT_FOUND)
            continue

        product_price = article["price"]
        if not product_price:
            logger.warning(error_messages.PRICE_NOT_FOUND)
            continue

        product_description = article["description"]
        if not product_description:
            logger.warning(error_messages.DESCRIPTION_NOT_FOUND)
            continue

        match_name = re.findall(search.replace(" ", ""), product_name.replace(" ", ""), flags=re.IGNORECASE)
        match_description = re.findall(desired_words, product_description, flags=re.IGNORECASE)
        if len(match_name) == 0 or len(match_description) == 0 or product_price < min_price or product_price > max_price:
            continue

        product = {
            "url": product_link,
            "name": product_name,
            "price": product_price,
            "updated_at": current_time,
            "wallapop_id": wallapop_id,
            "description": product_description,
        }

        db_article = db_session.query(Article).filter(Article.wallapop_id == wallapop_id).first()
        if db_article:
            if float(db_article.price) <= float(product_price):
                continue

            logger.warning(f"Se actualiza el producto: {wallapop_id} - {product_name} - {db_article.price} - {product_price}")
            db_session.query(UserArticle).filter(UserArticle.article_id == db_article._id).update({"notified": 0}, synchronize_session=False)
            db_session.query(Article).filter(Article.wallapop_id == wallapop_id).update(product, synchronize_session=False)
            db_session.commit()

        else:
            logger.warning(f"Se registra un nuevo producto: {wallapop_id} - {product_name}")
            new_article = Article(**product)
            db_session.add(new_article)
            db_session.commit()
            new_user_article = UserArticle(user_id=user_id, article_id=new_article._id)
            db_session.add(new_user_article)
            db_session.commit()

        articles_dict[wallapop_id] = True
    db_session.close()


async def main():
    USERS_DATA_DICT = {}

    db_session = Session()
    users_data = db_session.query(User).all()
    logger.warning(f"users_data: {users_data}")
    x = 0
    for user in users_data:
        user_id = user._id
        search = user.search

        ## Filtros para la descripción
        filter = user.filter
        desired_words = filter.get("description", None)
        min_price = filter.get("min_price", 0)
        max_price = filter.get("max_price", 1000000)

        ## Cantidad de busquedas
        n = 3
        url_list = []
        url_list += [URL_BASE + f"&start={(i)*40}" + f"&keywords={search}" for i in range(n)]

        USERS_DATA_DICT[x] = {}
        USERS_DATA_DICT[x]["user_id"] = user_id
        USERS_DATA_DICT[x]["url_list"] = url_list
        USERS_DATA_DICT[x]["desired_words"] = desired_words
        USERS_DATA_DICT[x]["min_price"] = min_price
        USERS_DATA_DICT[x]["max_price"] = max_price
        x += 1
    db_session.close()
    logger.warning(f"Ready to start consulting")
    try:
        conn = aiohttp.TCPConnector(limit=15)
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(connector=conn, headers=HEADERS, timeout=timeout) as aiohttp_session:
            for x in USERS_DATA_DICT:
                user_id = USERS_DATA_DICT[x]["user_id"]
                url_list = USERS_DATA_DICT[x]["url_list"]
                min_price = USERS_DATA_DICT[x]["min_price"]
                max_price = USERS_DATA_DICT[x]["max_price"]
                desired_words = USERS_DATA_DICT[x]["desired_words"]
                if user_id and url_list and desired_words:
                    await asyncio.gather(*[scrape_data(aiohttp_session, url, user_id, search, desired_words, min_price, max_price) for url in url_list])

    except asyncio.exceptions.TimeoutError:
        logger.error("TIMEOUT")

    await asyncio.sleep(0.250)
