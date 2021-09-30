from enum import Enum
from os.path import expanduser
from pathlib import Path


class Prompts:
    MSG_SAVE = 'Do you want to save the current session?'
    MSG_RESTORE = 'Do you want to restore the session named %s?'
    MSG_CLOSE_ALL_WINDOWS = 'Do you want to close windows?'
    MSG_POP_UP_A_DIALOG_TO_RESTORE = 'Do you want to restore the session named %s?'


class Locations:
    USER_HOME = str(expanduser('~'))

    # session configs

    BASE_LOCATION_OF_SESSIONS = Path(USER_HOME, '.config', 'xsession-manager', 'sessions')

    BASE_LOCATION_OF_BACKUP_SESSIONS = Path(USER_HOME, '.config', 'xsession-manager', 'sessions', 'backups')

    DEFAULT_SESSION_NAME = 'xsession-default'

    # Save the current x session to xsession-default
    LOCATION_OF_DEFAULT_SESSION = Path(BASE_LOCATION_OF_SESSIONS, DEFAULT_SESSION_NAME)

    # rule configs

    BASE_RULE_CONFIGS_PATH = Path(USER_HOME, '.config', 'xsession-manager', 'rule')
    RULE_CONFIGS_NAME = 'rule-configs.json'
    RULE_CONFIGS_PATH = Path(BASE_RULE_CONFIGS_PATH, RULE_CONFIGS_NAME)


class GSettings(Enum):

    dynamic_workspaces = 'org.gnome.mutter', 'dynamic-workspaces'
    workspaces_number = 'org.gnome.desktop.wm.preferences', 'num-workspaces'

    def __init__(self, schema: str, key: str):
        self.schema = schema
        self.key = key


