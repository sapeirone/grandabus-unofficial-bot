import logging

from firebase_admin import firestore as firestore_api
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove)
from telegram.ext import ConversationHandler, CallbackContext

from bot.decorators import exception_logger, with_firestore
from bot.handlers import states
from .start import on_start_command

logger = logging.getLogger(__name__)


def _get_enable_notifications_btn(code):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text="Abilita notifiche", callback_data=f'enable_notif_{code}')]
    ])


def _get_disable_notifications_btn(code):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text="Disabilita notifiche", callback_data=f'disable_notif_{code}')]
    ])


@exception_logger(logger)
def on_start_searching_by_line(update: Update, _):
    update.message.reply_text(
        "Digita il codice di una linea oppure torna al /menu",
        reply_markup=ReplyKeyboardRemove())
    return states.WAITING


@exception_logger(logger)
def on_start_searching_by_location(update: Update, _):
    update.message.reply_text(
        "Digita il nome di una città oppure torna al /menu",
        reply_markup=ReplyKeyboardRemove())
    return states.WAITING


@exception_logger(logger)
def on_back_to_menu(update: Update, context):
    on_start_command(update, context)
    return ConversationHandler.END


@exception_logger(logger)
@with_firestore()
def on_search_by_location(update: Update, context, firestore):
    # instantiate a new Firestore client
    name = update.message.text

    lines_ref = firestore.collection('lines')
    lines = lines_ref.where(u'cities', u'array_contains', name.upper()).stream()

    response = ''
    for line in lines:
        line = line.to_dict()
        response += f'👉 <b>{line["code"]}</b>\n' \
                    f'<b>Nome linea: </b>{line["name"]}\n' \
                    f'<b>Orari: </b>{line["timetable_url"]}\n\n'

    if response:
        update.message.reply_html(response, disable_web_page_preview=True)
    else:
        update.message.reply_text(
            "Nessuna linea trovata. Prova con un'altra città")

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Tocca /menu per tornare al menu")

    return ConversationHandler.END if response else states.WAITING


@exception_logger(logger)
@with_firestore()
def on_search_by_line(update: Update, context, firestore):
    # instantiate a new Firestore client
    name = update.message.text

    line = firestore.collection('lines').document(name).get()
    found = line.exists

    if not found:
        update.message.reply_html(f'😕 Impossibile trovare la linea {name}.')
    else:
        line = line.to_dict()
        cities = str.join('\n', map(lambda c: f' - {c}', line['cities']))

        if 'user_subscriptions' in line and update.effective_chat.id in line['user_subscriptions']:
            reply_markup = _get_disable_notifications_btn(line["code"])
        else:
            reply_markup = _get_enable_notifications_btn(line["code"])

        update.message.reply_html(f'👉 <b>{line["code"]}</b>\n'
                                  f'<b>Nome linea: </b>{line["name"]}\n\n'
                                  f'<b>Paesi: </b>\n{cities}\n\n', reply_markup=reply_markup)
        context.bot.send_document(chat_id=update.effective_chat.id, document=line['timetable_url'])

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Tocca /menu per tornare al menu")

    return ConversationHandler.END if found else states.WAITING


@exception_logger(logger)
@with_firestore()
def on_enable_notifications(update: Update, context: CallbackContext, firestore):
    code = update.callback_query.data.replace("enable_notif_", "")

    doc = firestore.collection(u'lines').document(code)

    doc.update({u'user_subscriptions': firestore_api.ArrayUnion([update.effective_chat.id])})

    update.callback_query.edit_message_reply_markup(reply_markup=_get_disable_notifications_btn(code))
    context.bot.answer_callback_query(update.callback_query.id, text='Notifiche abilitate')


@exception_logger(logger)
@with_firestore()
def on_disable_notifications(update: Update, context, firestore):
    code = update.callback_query.data.replace("disable_notif_", "")

    doc = firestore.collection(u'lines').document(code)

    doc.update({u'user_subscriptions': firestore_api.ArrayRemove([update.effective_chat.id])})

    update.callback_query.edit_message_reply_markup(reply_markup=_get_enable_notifications_btn(code))
    context.bot.answer_callback_query(update.callback_query.id, text='Notifiche disabilitate')
