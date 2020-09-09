import datetime
import json
import os
from pathlib import Path

import psutil
import sys

from types import SimpleNamespace as Namespace

import argparse

from settings import constants
from settings.constants import Locations
from settings.xsession_config_object import XSessionConfigObject
from utils import string_utils, wmctl_wapper, subprocess_utils


def check_and_reset_args(args: Namespace):
    save = args.save
    restore = args.restore
    list_sessions = args.list
    detail = args.detail
    close_all = args.close_all
    pop_up_a_dialog_to_restore = args.p

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

    print('Namespace object after handling by this program: ' + str(args))

    if save or restore or close_all:
        if list_sessions:
            raise argparse.ArgumentTypeError('argument -l/--list : '
                                             'not allowed with any argument of -s/--save, -r/--restore, -c/--close-all')
        if detail:
            raise argparse.ArgumentTypeError('argument -t/--detail : '
                                             'not allowed with any argument of -s/--save, -r/--restore, -c/--close-all')
        if pop_up_a_dialog_to_restore:
            raise argparse.ArgumentTypeError('argument -p : '
                                             'not allowed with any argument of -s/--save, -r/--restore, -c/--close-all')

    if close_all is False \
            and not string_utils.empty_string(restore):
        # get the opening windows via wmctl
        print("Opening windows list:")
        running_windows = wmctl_wapper.get_running_windows_raw()
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


def save_session(session_name: str):
    running_windows: list = wmctl_wapper.get_running_windows()
    session_details: list = XSessionConfigObject.convert_wmctl_result_2_list(running_windows)
    print('Got the process list according to wmctl: ' + str(session_details))
    for sd in session_details:
        process = psutil.Process(sd.pid)
        sd.app_name = process.name()
        sd.cmd = process.cmdline()
        sd.create_time = datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
    print('Complete the process list according to psutil: ' + str(session_details))

    session_details_json = json.dumps(session_details, default=lambda o: o.__dict__)
    print('Got the json format x session: ' + session_details_json)

    session_path = Path(Locations.BASE_LOCATION_OF_SESSIONS, session_name)
    print('Saving the session to: ' + str(session_path))

    if not session_path.exists():
        session_path.parent.mkdir(parents=True, exist_ok=True)

    with open(session_path, 'w') as file:
        file.write(
            json.dumps(
                json.loads(session_details_json),
                indent=4,
                sort_keys=True))


def restore_session(session_name):
    session_path = Path(Locations.BASE_LOCATION_OF_SESSIONS, session_name)
    if not session_path.exists():
        raise FileNotFoundError('Session file [%s] was not found.' % session_path)

    with open(session_path, 'r') as file:
        print('Restoring session located [%s] ' % session_path)
        namespace_objs = json.load(file, object_hook=lambda d: Namespace(**d))
        # Note: os.fork() does not support the Windows
        pid = os.fork()
        # Run commandlines in the child process
        # TODO: I'm not sure if this method works well and is the best practice
        if pid == 0:
            for namespace_obj in namespace_objs:
                cmd: list = namespace_obj.cmd
                app_name: str = namespace_obj.app_name
                print('Restoring application:              [%s]' % app_name)
                if len(cmd) == 0:
                    print('Failure to restore application: [%s] due to empty commandline [%s]' % (app_name, str(cmd)))
                    continue

                # Ignore the output for now
                subprocess_utils.run_cmd(cmd)

                print('Success to restore application:     [%s]' % app_name)


def handle_arguments(args: Namespace):
    session_name_for_saving = args.save
    session_name_for_restoring = args.restore
    list_sessions = args.list
    detail = args.detail
    close_all = args.close_all
    pop_up_a_dialog_to_restore = args.p

    if session_name_for_saving:
        print(constants.Prompts.MSG_SAVE)
        wait_for_answer()
        save_session(session_name_for_saving)

    if session_name_for_restoring:
        print(constants.Prompts.MSG_RESTORE % session_name_for_restoring)
        wait_for_answer()
        restore_session(session_name_for_restoring)


