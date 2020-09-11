from os.path import expanduser
from pathlib import Path


class Prompts:
    MSG_SAVE = 'Do you want to save the current session?'
    MSG_RESTORE = 'Do you want to restore the session named %s?'
    MSG_CLOSE_ALL_WINDOWS = 'Do you want to close all windows?'


class Locations:
    USER_HOME = str(expanduser('~'))

    BASE_LOCATION_OF_SESSIONS = Path(USER_HOME, '.config', 'xsession-manager', 'sessions')

    BASE_LOCATION_OF_BACKUP_SESSIONS = Path(USER_HOME, '.config', 'xsession-manager', 'sessions', 'backups')

    DEFAULT_SESSION_NAME = 'xsession-default'

    # Save the current x session to xsession-default
    LOCATION_OF_DEFAULT_SESSION = Path(BASE_LOCATION_OF_SESSIONS, 'xsession-default')


