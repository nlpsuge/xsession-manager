import datetime
import json
import os
import subprocess
from itertools import groupby
from multiprocessing import cpu_count
from multiprocessing.pool import Pool
from operator import attrgetter
from pathlib import Path
from time import time, sleep
from types import SimpleNamespace as Namespace
from typing import List

import psutil

from session_filter import SessionFilter
from settings.constants import Locations
from settings.xsession_config import XSessionConfig, XSessionConfigObject
from utils import wmctl_wrapper, subprocess_utils, gsettings_wrapper, retry


class XSessionManager:

    _moving_windows_pool: Pool

    session_filters: List[SessionFilter]
    base_location_of_sessions: str
    base_location_of_backup_sessions: str

    def __init__(self, session_filters: List[SessionFilter]=None,
                 base_location_of_sessions: str=Locations.BASE_LOCATION_OF_SESSIONS,
                 base_location_of_backup_sessions: str=Locations.BASE_LOCATION_OF_BACKUP_SESSIONS):
        self.session_filters = session_filters
        self.base_location_of_sessions = base_location_of_sessions
        self.base_location_of_backup_sessions = base_location_of_backup_sessions

    def save_session(self, session_name: str, session_filter: SessionFilter=None):
        x_session_config = self.get_session_details(session_filters=[session_filter])
        x_session_config.session_name = session_name

        session_path = Path(self.base_location_of_sessions, session_name)
        print('Saving the session to: ' + str(session_path))

        if not session_path.parent.exists():
            session_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Backup the old session
            if session_path.exists():
                self.backup_session(session_path)

        # Save a new session
        x_session_config.session_create_time = datetime.datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S.%f")
        save_session_details_json = json.dumps(x_session_config, default=lambda o: o.__dict__)
        print('Saving the new json format x session [%s] ' % save_session_details_json)
        self.write_session(session_path, save_session_details_json)
        print('Done!')

    def get_session_details(self, remove_duplicates_by_pid=True,
                            session_filters: List[SessionFilter]=None) -> XSessionConfig:

        """
        Get the current running session details, including app name, process id,
        window position, command line etc of each app. See XSessionConfigObject for more information.

        :return: the current running session details
        """

        running_windows: list = wmctl_wrapper.get_running_windows()
        x_session_config: XSessionConfig = XSessionConfigObject.convert_wmctl_result_2_list(running_windows,
                                                                                            remove_duplicates_by_pid)
        print('Got the process list according to wmctl: %s' % json.dumps(x_session_config, default=lambda o: o.__dict__))
        x_session_config_objects: List[XSessionConfigObject] = x_session_config.x_session_config_objects
        for idx, sd in enumerate(x_session_config_objects):
            try:
                process = psutil.Process(sd.pid)
                sd.app_name = process.name()
                sd.cmd = process.cmdline()
                sd.process_create_time = datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
            except psutil.NoSuchProcess as e:
                print('Failed to get process [%s] info using psutil due to: %s' % (sd, str(e)))
                sd.app_name = ''
                sd.cmd = []
                sd.process_create_time = None

        if session_filters is not None:
            for session_filter in session_filters:
                if session_filter is None:
                    continue
                x_session_config.x_session_config_objects[:] = \
                    session_filter(x_session_config.x_session_config_objects)

        print('Complete the process list according to psutil: %s' %
              json.dumps(x_session_config, default=lambda o: o.__dict__))
        return x_session_config

    def backup_session(self, original_session_path):
        backup_time = datetime.datetime.fromtimestamp(time())
        with open(original_session_path, 'r') as file:
            print('Backing up session located [%s] ' % original_session_path)
            namespace_objs: XSessionConfig = json.load(file, object_hook=lambda d: Namespace(**d))
        current_time_str_as_backup_id = backup_time.strftime("%Y%m%d%H%M%S%f")
        backup_session_path = Path(self.base_location_of_backup_sessions,
                                   os.path.basename(original_session_path) + '.backup-' + current_time_str_as_backup_id)
        if not backup_session_path.parent.exists():
            backup_session_path.parent.mkdir(parents=True, exist_ok=True)
        print('Backup the old session file [%s] to [%s]' % (original_session_path, backup_session_path))
        backup_time_str = backup_time.strftime("%Y-%m-%d %H:%M:%S.%f")
        namespace_objs.backup_time = backup_time_str
        backup_session_details_json = json.dumps(namespace_objs, default=lambda o: o.__dict__)
        self.write_session(backup_session_path, backup_session_details_json)

    def write_session(self, session_path, session_details_json):
        with open(session_path, 'w') as file:
            file.write(
                json.dumps(
                    json.loads(session_details_json),
                    indent=4,
                    sort_keys=True))

    def restore_session(self, session_name, restoring_interval=2):
        session_path = Path(self.base_location_of_sessions, session_name)
        if not session_path.exists():
            raise FileNotFoundError('Session file [%s] was not found.' % session_path)

        with open(session_path, 'r') as file:
            print('Restoring session located [%s] ' % session_path)
            namespace_objs: XSessionConfig = json.load(file, object_hook=lambda d: Namespace(**d))
            # Note: os.fork() does not support the Windows
            pid = os.fork()
            # Run command lines in the child process
            # TODO: I'm not sure if this method works well and is the best practice
            if pid == 0:
                x_session_config_objects: List[XSessionConfigObject] = namespace_objs.x_session_config_objects

                if self.session_filters is not None:
                    for session_filter in self.session_filters:
                        if session_filter is None:
                            continue
                        x_session_config_objects[:] = session_filter(x_session_config_objects)

                if len(x_session_config_objects) == 0:
                    print('No application to restore.')
                    print('Done!')
                    return

                def restore_sessions():
                    self._moving_windows_pool = Pool(processes=cpu_count())
                    for namespace_obj in x_session_config_objects:
                        cmd: list = namespace_obj.cmd
                        app_name: str = namespace_obj.app_name
                        print('Restoring application:              [%s]' % app_name)
                        if len(cmd) == 0:
                            print('Failure to restore application: [%s] due to empty commandline [%s]' % (app_name, str(cmd)))
                            continue

                        process = subprocess_utils.run_cmd(cmd)
                        # print('Success to restore application:     [%s]' % app_name)

                        self._move_window_async(namespace_obj, process)

                        # Wait some time, in case of freezing the entire system
                        sleep(restoring_interval)

                # Create enough workspaces
                if wmctl_wrapper.is_gnome():
                    # TODO No need to use int() because the type of 'desktop_number' should be int, something is wrong
                    max_desktop_number = int(max([x_session_config_object.desktop_number
                                                 for x_session_config_object in x_session_config_objects])) + 1
                    if gsettings_wrapper.is_dynamic_workspaces():
                        gsettings_wrapper.disable_dynamic_workspaces()
                        try:
                            gsettings_wrapper.set_workspaces_number(max_desktop_number)
                            restore_sessions()
                        except Exception as e:
                            import traceback
                            print(traceback.format_exc())
                        gsettings_wrapper.enable_dynamic_workspaces()
                    else:
                        workspaces_number = gsettings_wrapper.get_workspaces_number()
                        if max_desktop_number > workspaces_number:
                            gsettings_wrapper.set_workspaces_number(max_desktop_number)
                        restore_sessions()
                else:
                    restore_sessions()
                print('Done!')

    def close_windows(self):
        sessions: List[XSessionConfigObject] = \
            self.get_session_details(remove_duplicates_by_pid=False,
                                     session_filters=self.session_filters).x_session_config_objects

        if len(sessions) == 0:
            print('No application to close.')
            return

        sessions.sort(key=attrgetter('pid'))
        for pid, group_by_pid in groupby(sessions, key=attrgetter('pid')):
            a_process_with_many_windows = list(group_by_pid)
            if len(a_process_with_many_windows) > 1:
                a_process_with_many_windows.sort(key=attrgetter('window_id'), reverse=True)
                # Close one application's windows one by one from the last one
                for session in a_process_with_many_windows:
                    print('Closing %s(%s %s).' % (session.app_name, session.window_id, session.pid))
                    # No need to catch the CalledProcessError for now, I think.
                    # In one case, if failed to close one window via 'wmctrl -ic window_id', the '$?' will be 0.
                    # In this case, this application may not be closed successfully.
                    wmctl_wrapper.close_window_gracefully_sync(session.window_id)
            else:
                session = a_process_with_many_windows[0]
                print('Closing %s(%s %s).' % (session.app_name, session.window_id, session.pid))
                wmctl_wrapper.close_window_gracefully_async(session.window_id)

            # Wait some time, in case of freezing the entire system
            sleep(0.25)

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['_moving_windows_pool']
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)

    def _move_window_async(self, namespace_obj: XSessionConfigObject, process: subprocess.Popen):
        pid = process.pid
        self._moving_windows_pool.apply_async(
            retry.Retry(6, 1).do_retry(self._move_window, (namespace_obj, pid)))

    def _move_window(self, namespace_obj: XSessionConfigObject, pid: int):
        no_need_to_move = True
        moving_windows = []
        try:
            pids = [str(c.pid) for c in psutil.Process(pid).children()]
            pid_str = str(pid)
            pids.append(pid_str)
            desktop_number = namespace_obj.desktop_number

            # Get process info according to command line
            if len(moving_windows) == 0:
                cmd = namespace_obj.cmd
                pids = []
                for p in psutil.process_iter(attrs=['pid', 'cmdline']):
                    if p.cmdline() == cmd:
                        pids.append(str(p.pid))
                        break

            running_windows = wmctl_wrapper.get_running_windows()
            for running_window in running_windows:
                if running_window[2] in pids:
                    if running_window[1] != desktop_number:
                        moving_windows.append(running_window)
                        no_need_to_move = False
                else:
                    no_need_to_move = False

            if len(moving_windows) == 0:
                raise retry.NeedRetryException(namespace_obj)
            elif no_need_to_move:
                return

            for running_window in moving_windows:
                running_window_id = running_window[0]
                process = psutil.Process(pid)
                print('Moving window to desktop:           [%s: %s]' % (process.name(), desktop_number))
                wmctl_wrapper.move_window_to(running_window_id, desktop_number)
                # Wait some time to prevent 'X Error of failed request:  BadWindow (invalid Window parameter)'
                sleep(0.5)
        except retry.NeedRetryException as ne:
            raise ne
        except Exception as e:
            import traceback
            print(traceback.format_exc())
