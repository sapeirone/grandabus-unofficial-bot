from telegram.ext import Updater
from telegram.ext import messagequeue as mq

from .handlers import register_all_handlers


class GrandaBusBot(Updater):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_messages_queued_default = True
        self._msg_queue = mq.MessageQueue()

    def run(self, *args, **kwargs):
        """
        Attach all the handlers and run the bot
        """

        register_all_handlers(self)
        self.start_polling(*args, **kwargs)

    def add_handler(self, *args, **kwargs):
        """
        Shortcut for dispatcher.add_handler(*args, **kwargs)
        """
        self.dispatcher.add_handler(*args, **kwargs)

    def add_error_handler(self, *args, **kwargs):
        """
        Shortcut for dispatcher.add_error_handler(*args, **kwargs)
        """
        self.dispatcher.add_error_handler(*args, **kwargs)

    @mq.queuedmessage
    def send_queued_message(self, *args, **kwargs):
        self.bot.send_message(*args, **kwargs)

    @mq.queuedmessage
    def send_queued_document(self, *args, **kwargs):
        self.bot.send_document(*args, **kwargs)
