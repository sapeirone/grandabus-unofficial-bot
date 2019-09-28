import logging
import os

import requests
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CallbackContext

import bot.handlers.strings as strings
from bot.decorators import with_firestore, exception_logger

logger = logging.getLogger(__name__)

if 'LOCATIONIQ_API_KEY' not in os.environ:
    raise ValueError('Missing LOCATIONIQ_API_KEY environment variable')
LOCATIONIQ_API_KEY = os.environ['LOCATIONIQ_API_KEY']


def reverse_geocode_city(latitude, longitude):
    url = "https://us1.locationiq.com/v1/reverse.php"

    response = requests.get(url, params={
        'key': LOCATIONIQ_API_KEY,
        'lat': str(latitude),
        'lon': str(longitude),
        'format': 'json'
    })

    if response.status_code == 200:
        return response.json()['address']['city']
    else:
        raise IOError(f'Cannot reverse geocode ({latitude},{longitude}). LocationIQ replied {response.text}')


@exception_logger(logger)
@with_firestore()
def on_got_user_location(update: Update, context: CallbackContext, firestore):
    location = update.message.location

    if not location:
        raise ValueError('Expected location payload not found')

    # try to extract city name from location
    city = reverse_geocode_city(location.latitude, location.longitude).upper()

    lines_ref = firestore.collection('lines')
    lines = lines_ref.where(u'cities', u'array_contains', city).stream()
    lines = map(lambda l: l.to_dict(), lines)

    res = ''
    for line in lines:
        res += strings.short_line_descr(line['code'], line['name'], line['timetable_url'])

    if res:
        update.message.reply_html(res, disable_web_page_preview=True)
    else:
        update.message.reply_text(strings.no_line_found_by_location())

    context.bot.send_message(chat_id=update.effective_chat.id, text=strings.get_go_to_menu_message(),
                             reply_markup=ReplyKeyboardRemove())
