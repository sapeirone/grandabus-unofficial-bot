import logging

from telegram import (ChatAction,
                      Update, ReplyKeyboardMarkup,
                      ParseMode, KeyboardButton, ReplyKeyboardRemove)

from bot.decorators import send_action, with_firestore
from .strings import disclaimer_message
from .strings import start_message

logger = logging.getLogger(__name__)


@send_action(ChatAction.TYPING)
def on_disclaimer_command(update: Update, _):
    logger.info(f'User {update.effective_user.id} issued: /disclaimer')

    update.message.reply_markdown(disclaimer_message(),
                                  disable_web_page_preview=True,
                                  reply_markup=ReplyKeyboardRemove())


@send_action(ChatAction.TYPING)
@with_firestore()
def on_start_command(update: Update, context, firestore):
    logger.info(f'User {update.effective_user.id} issued: /start')

    doc = firestore.collection('scraper').document('last_session').get()
    date = doc.to_dict()['date'] if doc.exists else None

    markup = ReplyKeyboardMarkup([
        [KeyboardButton(u'🔢 Cerca per codice linea')],
        [KeyboardButton(u'🏙️ Cerca per località')],
        [KeyboardButton(u'📍 Invia posizione', request_location=True)]
    ], resize_keyboard=True, one_time_keyboard=True)

    context.bot.send_message(update.effective_chat.id,
                             start_message(date),
                             parse_mode=ParseMode.HTML,
                             reply_markup=markup,
                             disable_web_page_preview=True)
