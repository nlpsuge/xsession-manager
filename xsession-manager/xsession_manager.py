import datetime
import json
import os
from pathlib import Path
from time import time, sleep
from types import SimpleNamespace as Namespace

import psutil

from settings.constants import Locations
from settings.xsession_config import XSessionConfig, XSessionConfigObject
from utils import wmctl_wapper, subprocess_utils


def save_session(session_name: str):
    x_session_config = get_session_details()
    x_session_config.session_name = session_name

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


def get_session_details(remove_duplicates_by_pid=True) -> XSessionConfig:
    
    """
    Get the current running session details, including app name, process id, 
    window position, command line etc of each app. See XSessionConfigObject for more information.
    
    :return: the current running session details
    """
    
    running_windows: list = wmctl_wapper.get_running_windows()
    x_session_config: XSessionConfig = XSessionConfigObject.convert_wmctl_result_2_list(running_windows,
                                                                                        remove_duplicates_by_pid)
    print('Got the process list according to wmctl: ' + str(x_session_config))
    for sd in x_session_config.x_session_config_objects:
        process = psutil.Process(sd.pid)
        sd.app_name = process.name()
        sd.cmd = process.cmdline()
        sd.process_create_time = datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
    print('Complete the process list according to psutil: ' + str(x_session_config))
    return x_session_config


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
        # Run command lines in the child process
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
