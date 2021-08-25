import json
import sys
from pathlib import Path

from types import SimpleNamespace as Namespace

import argparse
from typing import List

from .gui.askyesno_dialog import create_askyesno_dialog
from .session_filter import ExcludeSessionFilter, IncludeSessionFilter
from .settings import constants
from .settings.constants import Locations
from .settings.xsession_config import XSessionConfigObject, XSessionConfig
from .utils import string_utils, wmctl_wrapper
from .xsession_manager import XSessionManager


def check_and_reset_args(args: Namespace):
    save = args.save
    restore = args.restore
    list_sessions = args.list
    detail = args.detail
    close_all = args.close_all
    pop_up_a_dialog_to_restore = args.pr
    move_automatically = args.move_automatically

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
    if string_utils.empty_string(detail) \
            and ('-t' in argv or '--detail' in argv):
        args.detail = Locations.DEFAULT_SESSION_NAME
        detail = args.detail
    if string_utils.empty_string(move_automatically) \
            and ('-ma' in argv or '--move-automatically' in argv):
        args.move_automatically = Locations.DEFAULT_SESSION_NAME
        move_automatically = args.move_automatically

    # -im/--including-apps-with-multiple-windows can only be used along with -c/--close-all
    if ('-im' in argv or '--including-apps-with-multiple-windows' in argv) and not ('-c' in argv or '--close-all' in argv):
        raise argparse.ArgumentTypeError('argument -im/--including-apps-with-multiple-windows : '
                                         'only allowed with -c/--close-all')

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
        if move_automatically:
            raise argparse.ArgumentTypeError('argument -ma/--move-automatically : '
                                             'not allowed with any argument of -s/--save, -r/--restore, -c/--close-all')

    if close_all is None \
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
        if str.lower(answer.strip()) not in ['n', 'y', '']:
            answer = input("Please type your answer again (y/N): ")
        else:
            break
    print('Your answer is: %s' % 'N' if answer.strip() == '' else answer.strip())
    if str.lower(answer.strip()) in ['n', '']:
        sys.exit(1)


def handle_arguments(args: Namespace):
    session_name_for_saving: str = args.save
    session_name_for_restoring: str = args.restore
    list_sessions = args.list
    session_details = args.detail
    close_all: list = args.close_all
    pop_up_a_dialog_to_restore = args.pr
    restoring_interval: int = args.restoring_interval
    exclude: list = args.exclude
    include: list = args.include
    move_automatically = args.move_automatically
    including_apps_with_multiple_windows = args.including_apps_with_multiple_windows

    if session_name_for_saving:
        print(constants.Prompts.MSG_SAVE)
        wait_for_answer()
        xsm = XSessionManager()
        xsm.save_session(session_name_for_saving)

    if close_all is not None:
        print(constants.Prompts.MSG_CLOSE_ALL_WINDOWS)
        wait_for_answer()
        # TODO Order sensitive?
        xsm = XSessionManager([IncludeSessionFilter(close_all),
                               IncludeSessionFilter(include),
                               ExcludeSessionFilter(exclude)])
        xsm.close_windows(including_apps_with_multiple_windows)
        print('Done!')

    if session_name_for_restoring:
        print(constants.Prompts.MSG_RESTORE % session_name_for_restoring)
        wait_for_answer()
        xsm = XSessionManager([IncludeSessionFilter(include),
                               ExcludeSessionFilter(exclude)])
        xsm.restore_session(session_name_for_restoring, restoring_interval)

    if pop_up_a_dialog_to_restore:
        answer = create_askyesno_dialog(constants.Prompts.MSG_POP_UP_A_DIALOG_TO_RESTORE
                                        % pop_up_a_dialog_to_restore)
        if answer:
            xsm = XSessionManager()
            xsm.restore_session(pop_up_a_dialog_to_restore, restoring_interval)

    if list_sessions:
        import os
        walk: (list, list, str) = os.walk(constants.Locations.BASE_LOCATION_OF_SESSIONS)
        for root, dirs, files in walk:
            # files.sort()
            for file in files:
                with open(Path(root, file), 'r') as f:
                    namespace_objs: XSessionConfig = json.load(f, object_hook=lambda d: Namespace(**d))
                    print(namespace_objs.session_name, namespace_objs.session_create_time, str(Path(root, file)),
                          sep='  ')

            break

    if session_details:
        session_path = Path(constants.Locations.BASE_LOCATION_OF_SESSIONS, session_details)
        print('Looking for session located [%s] ' % session_path)
        if not session_path.exists():
            print('[%s] not found.' % session_path)
            return

        print()
        count = 0
        with open(session_path, 'r') as file:
            namespace_objs: XSessionConfig = json.load(file, object_hook=lambda d: Namespace(**d))
            print('session name: %s' % namespace_objs.session_name)
            print('location: %s' % str(session_path))
            print('created at: %s' % namespace_objs.session_create_time)

            x_session_config_objects: List[XSessionConfigObject] = namespace_objs.x_session_config_objects
            # Print data according to declared order
            ordered_variables = vars(XSessionConfigObject)['__annotations__']
            for x_session_config_object in x_session_config_objects:
                count = count + 1
                print('%d.' % count)

                # Get fields in declared order
                x_session_config_object_annotations = vars(XSessionConfigObject)['__annotations__']

                vars_in_x_session_config_object = vars(x_session_config_object)
                keys_in_x_session_config_object = vars_in_x_session_config_object.keys()
                for ordered_key in ordered_variables.keys():
                    if ordered_key in keys_in_x_session_config_object:
                        value = vars_in_x_session_config_object[ordered_key]
                        if type(value) is Namespace:
                            # Print data according to declared order
                            _ordered_variables = \
                                vars(x_session_config_object_annotations[ordered_key])['__annotations__']
                            values = vars(value)
                            values_to_be_printed = []
                            for _ordered_key in _ordered_variables.keys():
                                if _ordered_key in values.keys():
                                    values_to_be_printed.append(_ordered_key.replace('_', ' ') + ": " +
                                                                str(values[_ordered_key]))
                            print('%s: %s' % (ordered_key.replace('_', ' '),
                                              ''.join('\n    ' + str(v) for v in values_to_be_printed)))
                        elif type(value) is list:
                            # Such as 'notepad-plus-plus.exe' via Snap has many empty strings in its cmdline
                            empty_slots_removed_str = ' '.join(ele for ele in value if ele != '')
                            print('%s: %s' % (ordered_key.replace('_', ' '), empty_slots_removed_str))
                        else:
                            print('%s: %s' % (ordered_key.replace('_', ' '), value))
                print()

    if move_automatically:
        xsm = XSessionManager([IncludeSessionFilter(include),
                               ExcludeSessionFilter(exclude)])
        xsm.move_window(move_automatically)
