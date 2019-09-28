import asyncio
import datetime
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import List

from firebase_admin import firestore
from telegram import ParseMode

from bot import GrandaBusBot
from bot.firestore_persistence import FirestorePersistence
from line import Line
from scraper import GrandaBusScraper
from utils.firebase_utils import init_firebase

if 'TELEGRAM_TOKEN' not in os.environ:
    raise ValueError("Environment variable 'TELEGRAM_TOKEN' required")

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']

init_firebase()
fs = firestore.client()

bot = GrandaBusBot(TELEGRAM_TOKEN, use_context=True, persistence=FirestorePersistence(fs))

scraper = GrandaBusScraper(fs)


def on_lines_deleted(lines: List[Line]):
    """
    Notify bot's users of deleted lines
    :param lines: deleted lines
    """
    for line in lines:
        for chat in line.user_subscriptions:
            bot.send_queued_message(chat_id=chat, text=f"⚠️⚠️⚠️\nLa linea {line.code} ({line.name}) è stata eliminata.",
                                    queued=True, parse_mode=ParseMode.MARKDOWN)


def on_lines_file_changed(lines: List[Line]):
    """
    Notify bot's users of changed lines
    :param lines: updated line
    """
    for line in lines:
        for chat in line.user_subscriptions:
            bot.send_queued_message(chat_id=chat,
                                    text=f"⚠️⚠️⚠️\nLa linea {line.code} ({line.name}) è stata aggiornata.",
                                    queued=True, parse_mode=ParseMode.MARKDOWN)
            bot.send_queued_document(chat_id=chat, document=line.url, queued=True)


async def scrape_every_day():
    await scraper.run()

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_with_time = datetime.datetime(
        year=tomorrow.year,
        month=tomorrow.month,
        day=tomorrow.day,
        minute=0,
        second=0,
        microsecond=0
    )
    loop.call_at(tomorrow_with_time.timestamp(), scrape_every_day)


async def main():
    bot.run()  # non blocking

    scraper.do_not_overwrite_if_unchanged = False
    scraper.on_lines_deleted = on_lines_deleted
    scraper.on_lines_file_changed = on_lines_file_changed

    await scrape_every_day()


if __name__ == '__main__':
    handler = TimedRotatingFileHandler("logs.log", when="midnight", interval=1)
    handler.suffix = "%Y%m%d"
    logging.basicConfig(level=logging.INFO, handlers=[handler])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
