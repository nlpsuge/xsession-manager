import json
import os
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


class ArgumentsHandler():
    
    def __init__(self, args: Namespace) -> None:
        self.args = args
        if self.args.vv:
            self.args.verbose = True
            
    def check_and_preset_args(self):
        save = self.args.save
        restore = self.args.restore
        list_sessions = self.args.list
        detail = self.args.detail
        close_all = self.args.close_all
        pop_up_a_dialog_to_restore = self.args.pr
        move_automatically = self.args.move_automatically
        
        verbose = self.args.verbose
        vv = self.args.vv

        if verbose:
            print('Namespace object before handling by this program: ' + str(self.args))

        # Need to deal with this kind of case when user type -s' '
        argv = [a.strip() for a in sys.argv[1:]]
        if verbose:
            print('Arguments input by user: ' + str(argv))
            
        if string_utils.empty_string(save) \
                and ('-s' in argv or '--save' in argv):
            self.args.save = Locations.DEFAULT_SESSION_NAME
            save = self.args.save
        if string_utils.empty_string(restore) \
                and ('-r' in argv or '--restore' in argv):
            self.args.restore = Locations.DEFAULT_SESSION_NAME
            restore = self.args.restore
        if string_utils.empty_string(pop_up_a_dialog_to_restore) \
                and ('-pr' in argv):
            self.args.pr = Locations.DEFAULT_SESSION_NAME
            pop_up_a_dialog_to_restore = self.args.pr
        if string_utils.empty_string(detail) \
                and ('-t' in argv or '--detail' in argv):
            self.args.detail = Locations.DEFAULT_SESSION_NAME
            detail = self.args.detail
        if string_utils.empty_string(move_automatically) \
                and ('-ma' in argv or '--move-automatically' in argv):
            self.args.move_automatically = Locations.DEFAULT_SESSION_NAME
            move_automatically = self.args.move_automatically

        # -im/--including-apps-with-multiple-windows can only be used along with -c/--close-all
        if ('-im' in argv or '--including-apps-with-multiple-windows' in argv) and not ('-c' in argv or '--close-all' in argv):
            raise argparse.ArgumentTypeError('argument -im/--including-apps-with-multiple-windows : '
                                            'only allowed with -c/--close-all')

        if verbose:
            print('Namespace object after handling by this program: ' + str(self.args))

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


    def wait_for_answer(self):
        answer = input("Please type your answer (y/N): ")
        while True:
            if str.lower(answer.strip()) not in ['n', 'y', '']:
                answer = input("Please type your answer again (y/N): ")
            else:
                break
        
        if self.args.verbose:
            print('Your answer is: %s' % ('N' if answer.strip() == '' else answer.strip()))
            
        if str.lower(answer.strip()) in ['n', '']:
            sys.exit(1)


    def handle_arguments(self):
        session_name_for_saving: str = self.args.save
        session_name_for_restoring: str = self.args.restore
        list_sessions = self.args.list
        session_details = self.args.detail
        close_all: list = self.args.close_all
        pop_up_a_dialog_to_restore = self.args.pr
        restoring_interval: int = self.args.restoring_interval
        exclude: list = self.args.exclude
        include: list = self.args.include
        move_automatically = self.args.move_automatically
        including_apps_with_multiple_windows = self.args.including_apps_with_multiple_windows

        if session_name_for_saving:
            print(constants.Prompts.MSG_SAVE % session_name_for_saving)
            self.wait_for_answer()
            xsm = XSessionManager(verbose=self.args.verbose, vv=self.args.vv)
            xsm.save_session(session_name_for_saving)

        # Empty close_all means close all windows
        if close_all is not None:
            print(constants.Prompts.MSG_CLOSE_ALL_WINDOWS)
            self.wait_for_answer()
            # TODO Order sensitive?
            xsm = XSessionManager(verbose=self.args.verbose,
                                  vv=self.args.vv,
                                  session_filters=[IncludeSessionFilter(close_all),
                                                   IncludeSessionFilter(include),
                                                   ExcludeSessionFilter(exclude)])
            xsm.close_windows(including_apps_with_multiple_windows)
            print('Done!')

        if session_name_for_restoring:
            if self.args.vv:
                print("Opening windows list:")
                running_windows = wmctl_wrapper.get_running_windows_raw()
                if len(running_windows) > 0:
                    for rw in running_windows:
                        print(rw)
                        
            print(constants.Prompts.MSG_RESTORE % session_name_for_restoring)
            self.wait_for_answer()
            xsm = XSessionManager(verbose=self.args.verbose,
                                  vv=self.args.vv,
                                  session_filters=[IncludeSessionFilter(include),
                                                   ExcludeSessionFilter(exclude)])
            xsm.restore_session(session_name_for_restoring, restoring_interval)

        if pop_up_a_dialog_to_restore:
            answer = create_askyesno_dialog(constants.Prompts.MSG_POP_UP_A_DIALOG_TO_RESTORE
                                            % pop_up_a_dialog_to_restore)
            if answer:
                xsm = XSessionManager(verbose=self.args.verbose, vv=self.args.vv)
                xsm.restore_session(pop_up_a_dialog_to_restore, restoring_interval)

        # Sort sessions based on modification time in ascending order
        if list_sessions:
            print()
            session_files = filter(lambda x: os.path.isfile(os.path.join(constants.Locations.BASE_LOCATION_OF_SESSIONS, x)), 
                                   os.listdir(constants.Locations.BASE_LOCATION_OF_SESSIONS) )
            session_files = sorted(session_files, 
                                   key = lambda x: os.path.getmtime(os.path.join(constants.Locations.BASE_LOCATION_OF_SESSIONS, x)))
            num = 0            
            for file in session_files:
                try:
                    file_path = Path(constants.Locations.BASE_LOCATION_OF_SESSIONS, file)
                    with open(file_path, 'r') as f:
                        num = num + 1
                        namespace_objs: XSessionConfig = json.load(f, object_hook=lambda d: Namespace(**d))
                        print(str(num) +'. ' + namespace_objs.session_name, 
                              namespace_objs.session_create_time, 
                              str(Path(constants.Locations.BASE_LOCATION_OF_SESSIONS, file)),
                              sep='  ')
                except:
                    print('Failed to list file: %s' % file_path)
                    import traceback
                    print(traceback.format_exc())
                
        if session_details:
            session_path = Path(constants.Locations.BASE_LOCATION_OF_SESSIONS, session_details)
            if self.args.verbose:
                print('Looking for session located [%s] ' % session_path)
            if not session_path.exists():
                print('[%s] not found.' % session_path)
                return

            print()
            count = 0
            with open(session_path, 'r') as file:
                namespace_objs: XSessionConfig = json.load(file, object_hook=lambda d: Namespace(**d))
                print('Session Name: %s' % namespace_objs.session_name)
                print('Created At: %s' % namespace_objs.session_create_time)
                print('Location: %s' % str(session_path))

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
            xsm = XSessionManager(verbose=self.args.verbose,
                                  vv=self.args.vv,
                                  session_filters=[IncludeSessionFilter(include),
                                                   ExcludeSessionFilter(exclude)])
            xsm.move_window(move_automatically)
