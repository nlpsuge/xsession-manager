import json
import re
from enum import Enum
from time import sleep

from ..utils import string_utils, wnck_utils
from .xsession_config import XSessionConfig, XSessionConfigObject
from .constants import Locations
from pynput.keyboard import Key, Controller, KeyCode


class Rules:

    class When:
        BEFORE = 'before', 'Before OperateType'
        REPLACE = 'replace', 'Replace OperateType'
        AFTER = 'after', 'After Before OperateType'

        def __init__(self, when: str, desc: str):
            self.when = when
            self.desc = desc

    class OperateType(Enum):

        CLOSE = 'close', 'When using -c/--close-all'
        RESTORE = 'restore', 'When using -r/--restore'

        def __init__(self, operate_type: str, desc: str):
            self.operateType = operate_type
            self.desc = desc

    class How(Enum):

        SHORTCUT = 'shortcut', 'Sending a shortcut to a Window'
        CODE = 'code', 'handle by code'

        def __init__(self, how, desc):
            self.how = how
            self.desc = desc

    default_configs = {
        'jetbrains': {
            OperateType.CLOSE.operateType: {
                'how': How.SHORTCUT.how,
                'when': When.REPLACE,
                'rule': 'Escape; Alt_L+F+X'
            }
            # ,
            # OperateType.RESTORE.operateType: {
            #     'how': How.CODE.how,
            #     'when': When.BEFORE,
            #     'rule': __get_jetbrains_path
            # }
        },
        'Ásbrú Connection Manager': {
            OperateType.CLOSE.operateType: {
                'how': How.SHORTCUT.how,
                'when': When.AFTER,
                'rule': 'space'
            }
        },
        'Oracle VM VirtualBox': {
            OperateType.CLOSE.operateType: {
                'how': How.SHORTCUT.how,
                'when': When.REPLACE,
                # 'rule': 'Alt_L+S; space'
                'rule': 'Control_R+H'
            }
        }

    }

    def __init__(self, x_session_config_object: XSessionConfigObject):
        self.x_session_config_object = x_session_config_object

    def apply_rules_if_needed(self, operate_type: OperateType, func, args):
        window_id_the_int_type = self.x_session_config_object.window_id_the_int_type
        rule_configs: dict = self.load_default_rule_configs().copy()
        rule_configs_from_file: dict = self.load_rule_configs_from_file()
        rule_configs.update(rule_configs_from_file)

        no_matched_rules = True

        for excepted_matched_key in rule_configs:
            if not self.__match_rule(excepted_matched_key):
                continue

            configs: dict = rule_configs[excepted_matched_key]
            if operate_type.operateType not in configs.keys():
                continue

            no_matched_rules = False

            when = configs[operate_type.operateType]['when']

            if when == Rules.When.AFTER:
                func(*args)

            if when == Rules.When.REPLACE:
                # No-op
                pass

            how = configs[operate_type.operateType]['how']
            if how == Rules.How.SHORTCUT.how:
                # Sleep sometime in case that windows is not responding for request
                # sleep()
                wnck_utils.focus_window(window_id_the_int_type)
                sleep(0.25)
                keyboard = Controller()
                shortcut: str = configs[operate_type.operateType]['rule']
                for key in shortcut.split(';'):
                    keys = key.strip().split('+')
                    for _key in keys:
                        keyboard.press(KeyCode._from_symbol(_key.strip()))

                    for _key in keys:
                        keyboard.release(KeyCode._from_symbol(_key.strip()))

            if how == Rules.How.CODE.how:
                pass

            if when == Rules.When.BEFORE:
                func(*args)

        if no_matched_rules:
            func(*args)

    def __match_rule(self, excepted_matched_key: str):
        if string_utils.empty_string(excepted_matched_key):
            return False

        app_name = self.x_session_config_object.app_name
        window_title = self.x_session_config_object.window_title

        return excepted_matched_key.lower() in app_name.lower() \
            or excepted_matched_key.lower() in window_title.lower()

    @staticmethod
    def load_rule_configs_from_file() -> dict:
        rule_configs_path = Locations.RULE_CONFIGS_PATH
        if not rule_configs_path.exists():
            return {}

        with open(rule_configs_path, 'r') as rule_config_file:
            rule_config_json = json.load(rule_config_file)
            return json.loads(rule_config_json)

    @staticmethod
    def load_default_rule_configs() -> dict:
        return Rules.default_configs



