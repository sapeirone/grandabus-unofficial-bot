import logging
from collections import defaultdict

from telegram.ext import BasePersistence


class FirestorePersistence(BasePersistence):
    """
    Using Google Firestore for making your Telegram bot persistent.

    This class does not use the best implementation possible for all situations.
    Data is stored into three top-level collections:
    - users: each document in this collection contains user-related data,
    - chat: each document in this collection contains chat-related data,
    - conversations: each document identifies a conversation. Inside each
      conversation data are stored following this structure:
        {
            "user_id": {
                "chat_id_1": {
                    ...
                },
                "chat_id_2": {
                    ...
                },
                ...
            },
            ...
        }

    The main downside of this implementation is that it requires a huge number
    of document reads each time the persistence data are restored from
    Firestore.

    """

    USER_COLLECTION = u'users'
    CHATS_COLLECTION = u'chats'
    CONVERSATIONS_COLLECTION = u'conversations'

    def __init__(self,
                 firestore_client,
                 logger: logging.Logger = logging.getLogger(__name__),
                 store_user_data=True,
                 store_chat_data=True):
        """Constructor

        :param logger: default logger
        :param store_user_data: whatever or not this class should store users' data
        :param store_chat_data: whatever or not this class should store chats' data
        """
        super(FirestorePersistence, self).__init__(store_user_data,
                                                   store_chat_data)
        self._logger = logger
        self._user_data = None
        self._chat_data = None
        self._conversations = None

        # instantiate a new Firestore client
        self.fs = firestore_client

    def get_user_data(self):
        """
        Extract previous users from the Firestore database
        :return: a dictionary of previous users.
        """
        if not self._user_data:
            self._user_data = defaultdict(dict)

            for user in self._get_users_collection().stream():
                self._user_data[user.id] = user.to_dict()

        return self._user_data

    def get_chat_data(self):
        """
        Extract previous chats from Firestore.
        :return: a dictionary of previous chats.
        """
        if not self._chat_data:
            self._chat_data = defaultdict(dict)

            for chat in self._get_chats_collection().stream():
                self._chat_data[chat.id] = chat.to_dict()

        return self._chat_data

    def get_conversations(self, name):
        """
        Extract previous conversations from Firestore.
        :param name: name of the conversation
        :return: a dictionary containing old conversations.
        """
        if not self._conversations:
            self._conversations = defaultdict(dict)

            for conversation in self._get_conversations_collection().stream():
                name = conversation.id  # name of the conversation
                self._conversations[name] = dict()

                for (user, chats) in conversation.to_dict().items():
                    for (chat, value) in chats.items():
                        # store conversations using (user, chat) as a key
                        self._conversations[name][(user, chat)] = value

        return self._conversations

    def _get_conversations_collection(self):
        return self.fs.collection(self.CONVERSATIONS_COLLECTION)

    def _get_chats_collection(self):
        return self.fs.collection(self.CHATS_COLLECTION)

    def _get_users_collection(self):
        return self.fs.collection(self.USER_COLLECTION)

    def update_conversation(self, name, key, new_state):
        """
        Update conversation related data

        :param name: name of the conversation
        :param key: key of the data to store
        :param new_state: conversation state
        """

        # extract user and chat ids from the conversation key
        user, chat = key

        try:
            self._get_conversations_collection().document(name).set({
                f"{user}": {
                    f"{chat}": new_state
                }
            }, merge=True)
        except Exception as e:
            self._logger.error(e)

    def update_user_data(self, user_id, data):
        """
        Update user related data

        :param user_id: id of the user
        :param data: data of the user to store
        """

        if data:
            try:
                self._get_users_collection().document(str(user_id)).set(data)
            except Exception as e:
                self._logger.error(e)

    def update_chat_data(self, chat_id, data):
        """
        Update chat related data

        :param chat_id: id of the chat
        :param data: data of the chat to store
        """
        if data:
            try:
                self._get_chats_collection().document(str(chat_id)).set(data)
            except Exception as e:
                self._logger.error(e)
