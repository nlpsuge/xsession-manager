import sys

from types import SimpleNamespace as Namespace

import argparse

import xsession_manager
from gui.askyesno_dialog import create_askyesno_dialog
from session_filter import SessionFilter
from settings import constants
from settings.constants import Locations
from settings.xsession_config import XSessionConfigObject
from utils import string_utils, wmctl_wrapper
from utils.number_utils import is_int, is_hexadecimal
from xsession_manager import save_session, restore_session, close_windows


def check_and_reset_args(args: Namespace):
    save = args.save
    restore = args.restore
    list_sessions = args.list
    detail = args.detail
    close_all = args.close_all
    pop_up_a_dialog_to_restore = args.pr

    # Need to deal with this kind of case when user type -s' '
    argv = [a.strip() for a in sys.argv[1:]]
    print('Arguments input by user: ' + str(argv))
    if string_utils.empty_string(save) \
            and ('-s' in argv or '--save' in argv):
        args.save = Locations.DEFAULT_SESSION_NAME
        save = args.save
    if string_utils.empty_string(restore) \
            and ('-r' in argv or '--restore' in argv):
        args.restore = Locations.DEFAULT_SESSION_NAME
        restore = args.restore
    if string_utils.empty_string(pop_up_a_dialog_to_restore) \
            and ('-pr' in argv):
        args.pr = Locations.DEFAULT_SESSION_NAME
        pop_up_a_dialog_to_restore = args.pr

    print('Namespace object after handling by this program: ' + str(args))

    if save or restore or close_all:
        if list_sessions:
            raise argparse.ArgumentTypeError('argument -l/--list : '
                                             'not allowed with any argument of -s/--save, -r/--restore, -c/--close-all')
        if detail:
            raise argparse.ArgumentTypeError('argument -t/--detail : '
                                             'not allowed with any argument of -s/--save, -r/--restore, -c/--close-all')
        if pop_up_a_dialog_to_restore:
            raise argparse.ArgumentTypeError('argument -pr : '
                                             'not allowed with any argument of -s/--save, -r/--restore, -c/--close-all')

    if close_all is False \
            and not string_utils.empty_string(restore):
        # get the opening windows via wmctl
        print("Opening windows list:")
        running_windows = wmctl_wrapper.get_running_windows_raw()
        if len(running_windows) > 0:
            for rw in running_windows:
                print(rw)
            print('Opening windows were found! Do you want to continue to restore a session?')
            wait_for_answer()
            print("Let's rock!")

        # Give user a warning
        # raise argparse.ArgumentTypeError('You must specify the \'-c/--close-all\' flags to close the current '
        #                                  'session before restoring a session.')


def wait_for_answer():
    answer = input("Please type your answer (y/N): ")
    while True:
        if str.lower(answer) not in ['n', 'y']:
            answer = input("Please type your answer again (y/N): ")
        else:
            break
    print('Your answer is: ' + answer)
    if str.lower(answer) == 'n':
        sys.exit(1)


class ExcludeSessionFilter(SessionFilter):

    excludes: list

    def __init__(self, excludes):
        self.excludes = excludes

    def __call__(self, session: XSessionConfigObject):
        for exclude in self.excludes:
            ii, value = is_int(exclude)
            if ii and value == session.pid:
                return True

            ih, value = is_hexadecimal(exclude)
            if ih and value == session.window_id:
                return True

            if exclude.lower() in session.app_name.lower() \
                    or exclude in session.window_title.lower():
                return True

        return super().__call__(session)


def handle_arguments(args: Namespace):
    session_name_for_saving: str = args.save
    session_name_for_restoring: str = args.restore
    list_sessions = args.list
    detail = args.detail
    close_all: bool = args.close_all
    pop_up_a_dialog_to_restore = args.pr
    restoring_interval: int = args.restoring_interval
    exclude: list = args.exclude

    if session_name_for_saving:
        print(constants.Prompts.MSG_SAVE)
        wait_for_answer()
        save_session(session_name_for_saving)

    if session_name_for_restoring:
        print(constants.Prompts.MSG_RESTORE % session_name_for_restoring)
        wait_for_answer()
        restore_session(session_name_for_restoring, restoring_interval)

    if close_all:
        print(constants.Prompts.MSG_CLOSE_ALL_WINDOWS)
        wait_for_answer()
        close_windows(ExcludeSessionFilter(exclude))
        print('Done!')

    if pop_up_a_dialog_to_restore:
        create_askyesno_dialog(constants.Prompts.MSG_POP_UP_A_DIALOG_TO_RESTORE
                               % pop_up_a_dialog_to_restore)
        restore_session(pop_up_a_dialog_to_restore, restoring_interval)





