import datetime
import json
import os
from pathlib import Path
from time import time, sleep

import psutil
import sys

from types import SimpleNamespace as Namespace

import argparse

from settings import constants
from settings.constants import Locations
from settings.xsession_config import XSessionConfigObject, XSessionConfig
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
    x_session_config: XSessionConfig = XSessionConfigObject.convert_wmctl_result_2_list(running_windows)
    x_session_config.session_name = session_name
    print('Got the process list according to wmctl: ' + str(x_session_config))
    for sd in x_session_config.x_session_config_objects:
        process = psutil.Process(sd.pid)
        sd.app_name = process.name()
        sd.cmd = process.cmdline()
        sd.process_create_time = datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
    print('Complete the process list according to psutil: ' + str(x_session_config))

    session_path = Path(Locations.BASE_LOCATION_OF_SESSIONS, session_name)
    print('Saving the session to: ' + str(session_path))

    if not session_path.parent.exists():
        session_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Backup the old session
        if session_path.exists():
            backup_session(session_path)

    # Save a new session
    x_session_config.session_create_time = datetime.datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S.%f")
    save_session_details_json = json.dumps(x_session_config, default=lambda o: o.__dict__)
    print('Saving the new json format x session [%s] ' % save_session_details_json)
    write_session(session_path, save_session_details_json)
    print('Done!')


def backup_session(original_session_path):
    backup_time = datetime.datetime.fromtimestamp(time())
    with open(original_session_path, 'r') as file:
        print('Backing up session located [%s] ' % original_session_path)
        namespace_objs = json.load(file, object_hook=lambda d: Namespace(**d))
    current_time_str_as_backup_id = backup_time.strftime("%Y%m%d%H%M%S%f")
    backup_session_path = Path(Locations.BASE_LOCATION_OF_BACKUP_SESSIONS,
                               os.path.basename(original_session_path) + '.backup-' + current_time_str_as_backup_id)
    if not backup_session_path.parent.exists():
        backup_session_path.parent.mkdir(parents=True, exist_ok=True)
    print('Backup the old session file [%s] to [%s]' % (original_session_path, backup_session_path))
    backup_time_str = backup_time.strftime("%Y-%m-%d %H:%M:%S.%f")
    namespace_objs.backup_time = backup_time_str
    backup_session_details_json = json.dumps(namespace_objs, default=lambda o: o.__dict__)
    write_session(backup_session_path, backup_session_details_json)


def write_session(session_path, session_details_json):
    with open(session_path, 'w') as file:
        file.write(
            json.dumps(
                json.loads(session_details_json),
                indent=4,
                sort_keys=True))


def restore_session(session_name, restoring_interval=2):
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
            for namespace_obj in namespace_objs.x_session_config_objects:
                cmd: list = namespace_obj.cmd
                app_name: str = namespace_obj.app_name
                print('Restoring application:              [%s]' % app_name)
                if len(cmd) == 0:
                    print('Failure to restore application: [%s] due to empty commandline [%s]' % (app_name, str(cmd)))
                    continue

                # Ignore the output for now
                subprocess_utils.run_cmd(cmd)
                print('Success to restore application:     [%s]' % app_name)

                sleep(restoring_interval)
            print('Done!')


def handle_arguments(args: Namespace):
    session_name_for_saving = args.save
    session_name_for_restoring = args.restore
    list_sessions = args.list
    detail = args.detail
    close_all = args.close_all
    pop_up_a_dialog_to_restore = args.p
    restoring_interval = args.restoring_interval

    if session_name_for_saving:
        print(constants.Prompts.MSG_SAVE)
        wait_for_answer()
        save_session(session_name_for_saving)

    if session_name_for_restoring:
        print(constants.Prompts.MSG_RESTORE % session_name_for_restoring)
        wait_for_answer()
        restore_session(session_name_for_restoring, restoring_interval)


