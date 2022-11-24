import asyncio
import html
import json
import logging
import traceback

import telegram.bot
from sqlalchemy import and_
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import Unauthorized
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, ConversationHandler, Filters, MessageHandler, Updater

import send_message
import utils.private_data as private_data
import utils.variables as variables
import wallapop
from database.models.Article import Article
from database.models.base import Session
from database.models.User import User
from database.models.UserArticle import UserArticle
from utils.parse_number import parseNumber

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables
(SENTENCE, LINK, CHAT_ID, TYPE_SELECTED) = ["frase", "enlace", "chat_id", "tipo"]
START_OVER = False

# States
(SELECTING_ACTION, ASKING_WORD, ADDING_SENTENCE, STOPPING, SELECT_OPT, SELECT_WORD, SHOW_SEARCHS, DELETION, SAVE_TEMPLATE) = map(chr, range(9))

# Unicode emojis
pencil = "\U0000270F"
cross_mark = "\U0000274C"
magnifiying = "\U0001F50E"
back = "\U0001F519"


# Shortcut for ConversationHandler.END
END = ConversationHandler.END

updater = Updater(private_data.BOT_TOKEN, workers=32, use_context=True)
job_queue = updater.job_queue

# Get the dispatcher to register handlers
dispatcher = updater.dispatcher


########################
# Callback
########################
def telegram_callback_error(update: object, context: CallbackContext):
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    #  logger.error(msg="Exception while handling an update:", exc_info=context.error)

    logger.error(f"Exception while handling an update: {context.error}")

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    context.bot.send_message(chat_id=private_data.DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML)


def telegram_back_with_msg(user_id, text, context, update):
    buttons = [[InlineKeyboardButton(text=f"{back} Volver", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)
    context.user_data[START_OVER] = True

    try:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    except:
        dispatcher.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard)

    return


########################
# Anti-spam
########################
def is_spam(user_id):
    user_id_int = int(user_id)

    if user_id_int != private_data.DEVELOPER_CHAT_ID:
        return True
    return False


########################
# Send a message to the user
########################
def send_user_alert(msg, user_id):

    try:
        dispatcher.bot.send_message(chat_id=user_id, text=msg, parse_mode="MarkdownV2")
        return True

    except Unauthorized as e:

        logger.error(f"Unauthorized user_id {user_id} with error: {e}")
        return False


########################
# Check for new articles
########################
def check_articles(context: telegram.ext.CallbackContext):
    result = asyncio.run(wallapop.main())
    # if result:
    #     logger.info("Se ha ejecutado correctamente la comprobación de productos")
    # else:
    #     logger.warning("Ha fallado la comprobación de productos")


########################
# Send an alert to the user
########################
def alert_user(context: telegram.ext.CallbackContext):
    result = send_message.main()
    # if result:
    #     logger.info("Se ha ejecutado correctamente el envío de mensajes")
    # else:
    #     logger.warning("Ha fallado el envío de mensajes")


########################
# Mostrar búsquedas
########################
def show_searchs(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.callback_query.message.chat.id
    except:
        user_id = update.message.chat.id

    spam = is_spam(user_id)
    if spam == True:
        logger.warning(f"User: {user_id} - Spam: {spam}")
        return END
    else:
        logger.info(f"User: {user_id} - Spam: {spam}")

    session = Session()
    user_data = session.query(User).filter(User.telegram_id == user_id).all()
    if not user_data:
        text = "No hay búsquedas registradas"

    else:
        text = "Estas son las búsquedas con filtros que tienes registradas:\n\n"

        for data in user_data:
            data = data.__dict__
            logger.warning(data)
            search = data.get("search")
            filter_data = data.get("filter", {})

            filter = filter_data.get("description", None).replace("|", "\\|")
            min_price = str(parseNumber(filter_data.get("min_price", 0))).replace(".", "\\.")
            max_price = str(parseNumber(filter_data.get("max_price", 0))).replace(".", "\\.")
            text += f"{pencil} Búsqueda: {search} \n        Filtros: {filter} \n        Precio mínimo: {min_price} € \n        Precio máximo: {max_price} € \n"
    session.close()

    buttons = [[InlineKeyboardButton(text=f"{back} Volver", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="MarkdownV2")

    context.user_data[START_OVER] = True
    logger.info(f"All registered sentence have been sent to {user_id}")
    return SELECTING_ACTION


########################
# Borrar una búsqueda
########################
def show_search_to_delete(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.callback_query.message.chat.id
    except:
        user_id = update.message.chat.id

    spam = is_spam(user_id)
    if spam == True:
        logger.warning(f"User: {user_id} - Spam: {spam}")
        return END
    else:
        logger.info(f"User: {user_id} - Spam: {spam}")

    buttons = []
    session = Session()
    user_data = session.query(User).filter(User.telegram_id == user_id)
    # user_data = db_manager.users_filters.perform_select(select_params={"search"}, search_params={"user_id": str(user_id)}, as_dict=True)
    try:
        searchs = []
        for data in user_data:
            data = data.__dict__
            searchs.append(data.get("search"))
    except:
        searchs = None
    session.close()

    if not searchs:
        text = "No hay búsquedas registradas"

    else:
        text = "Selecciona la búsqueda ha borrar\n\n"

        for search in searchs:
            button = [InlineKeyboardButton(text=search, callback_data=search)]
            buttons.append(button)

    buttons.append([InlineKeyboardButton(text=f"{back} Volver", callback_data=str(END))])
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return DELETION


def delete_one_search(update: Update, context: CallbackContext) -> None:
    volver = update.callback_query.data
    if volver == str(END):
        return SELECTING_ACTION

    search = str(update.callback_query.data)
    logger.warning(search)

    user_id = update.callback_query.message.chat.id
    try:
        session = Session()
        session.query(User).filter(and_(User.telegram_id == user_id, User.search == search)).delete()
        session.commit()
        session.close()
        text = "La búsqueda ha sido eliminada"
    except:
        text = "La búsqueda no ha podido ser eliminada"

    buttons = [[InlineKeyboardButton(text=f"{back} Volver", callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    logger.info(f"A search of {user_id}, has been deleted - search: {search}")

    context.user_data[START_OVER] = True
    return SELECTING_ACTION


########################
# Añadir nueva búsqueda
########################
def send_template(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.callback_query.message.chat.id)
    except:
        user_id = str(update.message.chat.id)

    spam = is_spam(user_id)
    if spam == True:
        logger.warning(f"User: {user_id} - Spam: {spam}")
        return END
    else:
        logger.info(f"User: {user_id} - Spam: {spam}")

    user_id = str(user_id)
    if user_id == str(private_data.DEVELOPER_CHAT_ID):
        context.user_data[CHAT_ID] = user_id

        text = "Debes rellenar el siguiente formulario cambiando las X por sus preferencias:"
        text2 = (
            "\\{"
            + "\\'busqueda\\' \\: \\'XXXX\\'\\, "
            + "\\'filtros\\' \\: \\'XXXX\\', "
            + "\\'precio\\_minimo\\' \\: \\'XXXX\\', "
            + "\\'precio\\_maximo\\' \\: \\'XXXX\\' "
            + "\\}"
        )

        text3 = (
            "Ejemplo: \n\n"
            + "\\{"
            + "\\'busqueda\\' \\: \\'BMW S1000RR\\'\\, "
            + "\\'filtros\\' \\: \\'2016\\|2017\\|2018\\', "
            + "\\'precio\\_minimo\\' \\: \\'5000\\', "
            + "\\'precio\\_maximo\\' \\: \\'12000\\' "
            + "\\} \n\n"
            + "Utiliza la plantilla superior, solo debes enviar el formulario modificando las 'X' y sin introducir otras palabras fuera de los corchetes"
        )

        update.callback_query.answer(text=text)
        update.callback_query.edit_message_text(text=text)

        dispatcher.bot.send_message(chat_id=user_id, text=text2, parse_mode="MarkdownV2")
        dispatcher.bot.send_message(chat_id=user_id, text=text3, parse_mode="MarkdownV2")

        return SAVE_TEMPLATE

    else:
        text = "No sé quien eres"
        telegram_back_with_msg(user_id=user_id, text=text, context=context, update=update)
        return END


def save_template(update: Update, context: CallbackContext) -> None:
    try:
        volver = update.callback_query.data
        if volver == str(END):
            return SELECTING_ACTION
    except:
        pass

    try:
        user_id = str(update.callback_query.message.chat.id)
    except:
        user_id = str(update.message.chat.id)

    spam = is_spam(user_id)
    if spam == True:
        logger.warning(f"User: {user_id} - Spam: {spam}")
        return END
    else:
        logger.info(f"User: {user_id} - Spam: {spam}")

    user_id = str(user_id)
    if user_id == str(private_data.DEVELOPER_CHAT_ID):
        context.user_data[CHAT_ID] = user_id

        try:
            template = str(update.message.text)
            template = template.replace("'", '"')
            template = json.loads(template)
        except:
            text = "Formulario incorrecto. Asegúrate de solo modificar las 'X'"
            telegram_back_with_msg(user_id=user_id, text=text, context=context, update=update)
            return SELECTING_ACTION

        try:
            min_price = float(parseNumber(template.get("precio_minimo").replace("€", "")))
            max_price = float(parseNumber(template.get("precio_maximo").replace("€", "")))
        except:
            text = "Formulario incorrecto. Asegúrate que has indicado correctamente los precios"
            telegram_back_with_msg(user_id=user_id, text=text, context=context, update=update)
            return SELECTING_ACTION

        template["search"] = template.get("busqueda").upper()
        template["filter"] = {"description": template.get("filtros"), "min_price": min_price, "max_price": max_price}

        for i in variables.SPECIAL_CHARS:
            if i == "|":
                continue

            if template.get("filtros").find(i) != -1:
                text = "Formulario incorrecto. Utiliza los separadores | para cada palabra que añadas como filtro"
                telegram_back_with_msg(user_id=user_id, text=text, context=context, update=update)
                return SELECTING_ACTION

        logger.warning(template)

        session = Session()
        user = User(telegram_id=user_id, filter=template["filter"], search=template["search"])
        session.add(user)
        session.commit()
        session.close()
        buttons = [[InlineKeyboardButton(text=f"{back} Volver", callback_data=str(END))]]
        keyboard = InlineKeyboardMarkup(buttons)
        text = "Estupendo\\! La busqueda ha sido añadida"
        dispatcher.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard, parse_mode="MarkdownV2")

        return SELECTING_ACTION

    else:
        text = "No sé quien eres"

        buttons = [[InlineKeyboardButton(text=f"{back} Volver", callback_data=str(END))]]
        keyboard = InlineKeyboardMarkup(buttons)
        context.user_data[START_OVER] = True

        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

        return END


########################
# Menu inicial
########################
msg_inicial = "Hola! Soy un Bot y me encargo de avisar de nuevos productos de Wallapop"
text_inicial = "Si el menú no le responde o existe algún problema, pruebe a introducir /salir y vuelva a iniciar la conversación con /menu"

# Top level conversation callbacks
def menu(update: Update, context: CallbackContext) -> None:
    callback = 0
    try:
        user_id = update.callback_query.message.chat.id
        callback = 1
    except:
        user_id = update.message.chat.id
        callback = 2

    spam = is_spam(user_id)
    if spam == True:
        logger.warning(f"User: {user_id} - Spam: {spam}")
        return END
    else:
        logger.info(f"User: {user_id} - Spam: {spam}")

    if str(user_id) != "0":
        """Selecionar una acción"""
        buttons = [
            [InlineKeyboardButton(text=f"{pencil} Añadir búsqueda", callback_data=str("ADD_SEARCH"))],
            [InlineKeyboardButton(text=f"{cross_mark} Borrar búsqueda", callback_data=str("DELETE_SEARCH"))],
            [InlineKeyboardButton(text=f"{magnifiying} Mostrar búsquedas", callback_data=str("SHOW_SEARCHS"))],
            [InlineKeyboardButton(text="Salir", callback_data=str(END))],
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        # If we're starting over we don't need do send a new message
        try:
            if context.user_data.get(START_OVER) and callback == 1:
                logger.warning("Menu 1 - Volver")
                update.callback_query.answer()
                update.callback_query.edit_message_text(text=text_inicial, reply_markup=keyboard)
            elif callback == 1:
                logger.warning("Menu 2")
                update.callback_query.answer(msg_inicial)
                update.callback_query.edit_message_text(text=text_inicial, reply_markup=keyboard)
            else:
                logger.warning("Menu 3 - Menu comando")
                update.message.reply_text(msg_inicial)
                update.message.reply_text(text=text_inicial, reply_markup=keyboard)

        except:
            logger.warning(f"Menu except {callback}")

    else:
        update.message.reply_text(text="En mantenimiento, temporalmente desactivado.")
        context.user_data[START_OVER] = True
        return STOPPING

    context.user_data[START_OVER] = False
    return SELECTING_ACTION


########################
# Cerrar niveles
########################
def stop_nested(update: Update, context: CallbackContext) -> None:
    """Completely end conversation from within nested conversation."""
    update.message.reply_text("¡Hasta pronto!")

    return STOPPING


def stop(update: Update, context: CallbackContext) -> None:
    """End Conversation by command."""
    update.message.reply_text("¡Hasta pronto!")

    return END


def end_first_level(update: Update, context: CallbackContext) -> None:
    """End conversation from InlineKeyboardButton."""
    update.callback_query.answer()

    text = "Hasta pronto!"
    update.callback_query.edit_message_text(text=text)

    return END


def end_second_level(update: Update, context: CallbackContext) -> None:
    """Return to top level conversation."""
    context.user_data[START_OVER] = True
    menu(update, context)

    return END


########################
# Main
########################
def main():

    # Set up second level ConversationHandler (add product)
    add_word = ConversationHandler(
        entry_points=[CallbackQueryHandler(send_template, pattern="^" + str("ADD_SEARCH") + "$")],
        states={SAVE_TEMPLATE: [MessageHandler(Filters.text, save_template)]},
        fallbacks=[
            CallbackQueryHandler(end_second_level, pattern="^" + str(END) + "$"),
            CommandHandler("salir", stop_nested),
            CommandHandler("menu", menu),
            CommandHandler("start", menu),
        ],
        map_to_parent={
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation alltogether
            STOPPING: STOPPING,
        },
    )

    # Set up second level ConversationHandler (delete_word)
    delete_word = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_search_to_delete, pattern="^" + str("DELETE_SEARCH") + "$")],
        states={
            SELECT_WORD: [CallbackQueryHandler(show_search_to_delete, pattern="^" + str("DELETE_SEARCH") + "$")],
            DELETION: [CallbackQueryHandler(delete_one_search, pattern="\w+")],
        },
        fallbacks=[
            CallbackQueryHandler(end_second_level, pattern="^" + str(END) + "$"),
            CommandHandler("salir", stop_nested),
            CommandHandler("menu", menu),
            CommandHandler("start", menu),
        ],
        map_to_parent={
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation alltogether
            STOPPING: STOPPING,
        },
    )

    # Set up second level ConversationHandler (delete_word)
    show_word = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_searchs, pattern="^" + str("SHOW_SEARCHS") + "$")],
        states={SHOW_SEARCHS: [CallbackQueryHandler(show_searchs, pattern="^" + str("SHOW_SEARCHS") + "$")]},
        fallbacks=[
            CallbackQueryHandler(end_second_level, pattern="^" + str(END) + "$"),
            CommandHandler("salir", stop_nested),
            CommandHandler("menu", menu),
            CommandHandler("start", menu),
        ],
        map_to_parent={
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation alltogether
            STOPPING: STOPPING,
        },
    )

    # Set up top level ConversationHandler (selecting action)
    selection_handlers = [
        add_word,
        delete_word,
        show_word,
        CommandHandler("menu", menu),
        CommandHandler("start", menu),
        CallbackQueryHandler(end_first_level, pattern="^" + str(END) + "$"),
        CallbackQueryHandler(menu, pattern="^" + str(END) + "$"),
    ]

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("menu", menu), CommandHandler("start", menu)],
        states={SELECTING_ACTION: selection_handlers, STOPPING: [CommandHandler("menu", menu)]},
        fallbacks=[CommandHandler("salir", stop), CommandHandler("menu", menu), CommandHandler("start", menu)],
    )

    job_check_articles = job_queue.run_repeating(check_articles, interval=300, first=15)
    job_send_messages = job_queue.run_repeating(alert_user, interval=60, first=60)

    dispatcher.add_handler(conv_handler)
    dispatcher.add_error_handler(telegram_callback_error, run_async=False)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
