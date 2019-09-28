import os

import firebase_admin
from firebase_admin import credentials


def init_firebase():
    # noinspection PyProtectedMember
    if len(firebase_admin._apps):
        # Firebase is already initialized, nothing left to do here
        return

    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', None)
    if not credentials_file:
        raise ValueError("Missing GOOGLE_CREDENTIALS_FILE environment "
                         "variable")

    try:
        cred = credentials.Certificate(credentials_file)
        firebase_admin.initialize_app(cred)
    except IOError as e:
        raise IOError(f"Cannot read the credentials file provided: {e}")
    except ValueError as e:
        raise ValueError(f"Cannot instantiate firebase: {e}")
