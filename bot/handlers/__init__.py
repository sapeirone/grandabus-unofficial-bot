from telegram.ext import CommandHandler, MessageHandler, \
    Filters, CallbackQueryHandler

from bot.handlers import states
from .location import on_got_user_location
from .search import *
from .start import on_start_command, on_disclaimer_command

logger = logging.getLogger(__name__)


def error(update, context):
    logger.error('Update "%s" caused error "%s"', update, context.error)


def register_all_handlers(bot):
    bot.add_handler(CommandHandler('disclaimer', on_disclaimer_command))
    bot.add_handler(CommandHandler('start', on_start_command))
    bot.add_handler(CommandHandler('menu', on_start_command))

    bot.add_handler(CallbackQueryHandler(on_enable_notifications, pattern=r'enable_notif_\d*'))
    bot.add_handler(CallbackQueryHandler(on_disable_notifications, pattern=r'disable_notif_\d*'))

    bot.add_handler(MessageHandler(Filters.location, on_got_user_location))

    bot.add_handler(ConversationHandler(
        name='search_by_line_code',
        entry_points=[MessageHandler(Filters.regex("Cerca per codice linea"),
                                     on_start_searching_by_line)],
        states={
            states.WAITING: [CommandHandler('menu', on_back_to_menu),
                             MessageHandler(Filters.text, on_search_by_line)],
        },
        fallbacks=[MessageHandler(Filters.all, on_start_command)]
    ))

    bot.add_handler(ConversationHandler(
        name='search_by_location',
        entry_points=[MessageHandler(Filters.regex("Cerca per località"),
                                     on_start_searching_by_location)],
        states={
            states.WAITING: [
                CommandHandler('menu', on_back_to_menu),
                MessageHandler(Filters.text, on_search_by_location),
            ],
        },
        fallbacks=[MessageHandler(Filters.all, on_start_command)]
    ))

    bot.add_error_handler(error)
