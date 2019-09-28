import logging
from functools import wraps

from firebase_admin import firestore
from telegram import Update
from telegram.ext import CallbackContext


def exception_logger(logger: logging.Logger):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(e)
                raise e

        return wrapper

    return decorator


# Telegram send action
def send_action(chat_action):
    def wrapper(func):
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
            context.bot.send_chat_action(update.effective_chat.id, chat_action)
            return func(update, context, *args, **kwargs)

        return wrapped

    return wrapper


__cached_firestore_client = None


# decorator that injects a firestore instance
def with_firestore():
    def wrapper(func):
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
            global __cached_firestore_client

            if __cached_firestore_client is None:
                __cached_firestore_client = firestore.client()

            kwargs['firestore'] = __cached_firestore_client
            return func(update, context, *args, **kwargs)

        return wrapped

    return wrapper
