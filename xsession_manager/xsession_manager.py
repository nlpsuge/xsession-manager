import collections
import copy
import datetime
import json
import os
import threading
import traceback
from contextlib import contextmanager
from itertools import groupby
from multiprocessing import cpu_count
from multiprocessing.pool import Pool
from operator import attrgetter
from pathlib import Path
from subprocess import CalledProcessError
from time import time, sleep
from types import SimpleNamespace as Namespace
from typing import List, Dict, Any, Union

import psutil

from .session_filter import SessionFilter
from .settings.constants import Locations
from .settings.xsession_config import XSessionConfig, XSessionConfigObject
from .utils import wmctl_wrapper, subprocess_utils, retry, gio_utils, wnck_utils, snapd_workaround, suppress_output, \
    string_utils


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

        self._moved_windowids_cache = []
        self._suppress_log_if_already_in_workspace = False
        self.opened_window_id_pid: Dict[int, List[int]] = {}
        self.opened_window_id_pid_old: Dict[int, List[int]] = {}
        self.opened_window_id_pid_lock = threading.RLock()
        self._windows_can_not_be_moved: List[XSessionConfigObject] = []
        self._if_restore_geometry = False
        self.silence = False

    def save_session(self, session_name: str, session_filter: SessionFilter=None):
        x_session_config = self.get_session_details(remove_duplicates_by_pid=False,
                                                    session_filters=[session_filter])
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
        window position, command line etc of each app.

        See XSessionConfigObject for more information.

        :return: the current running session details
        """

        running_windows: list = wmctl_wrapper.get_running_windows()
        x_session_config: XSessionConfig = XSessionConfigObject.convert_wmctl_result_2_list(running_windows,
                                                                                            remove_duplicates_by_pid)
        if self.silence is False:
            print('Got the process list according to wmctl: %s' % json.dumps(x_session_config, default=lambda o: o.__dict__))
        x_session_config_objects: List[XSessionConfigObject] = x_session_config.x_session_config_objects
        for idx, sd in enumerate(x_session_config_objects):
            try:
                process = psutil.Process(sd.pid)
                sd.cmd = process.cmdline()
                sd.app_name = wnck_utils.get_app_name(sd.window_id_the_int_type)
                sd.process_create_time = datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
                sd.cpu_percent = process.cpu_percent()
                sd.memory_percent = process.memory_percent()
                sd.window_state = sd.WindowState()
                sd.window_state.is_above = wnck_utils.is_above(sd.window_id_the_int_type)
                sd.window_state.is_sticky = wnck_utils.is_sticky(sd.window_id_the_int_type)

                geometry = wnck_utils.get_geometry(sd.window_id_the_int_type)
                if geometry is None:
                    sleep(0.25)
                    geometry = wnck_utils.get_geometry(sd.window_id_the_int_type)
                if geometry:
                    x_offset, y_offset, width, height = geometry
                    window_position = sd.WindowPosition()
                    window_position.x_offset = x_offset
                    window_position.y_offset = y_offset
                    window_position.width = width
                    window_position.height = height
                    window_position.provider = 'Wnck'
                    sd.window_position = window_position
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

        if self.silence is False:
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
            # TODO 1. I'm not sure if this method works well and is the best practice
            # TODO 2. Must run in the child process or receive this error:
            # Gdk-Message: 23:23:24.613: main.py: Fatal IO error 11 (Resource temporarily unavailable) on X server :1
            # Not know the root cause
            if pid == 0:
                x_session_config_objects: List[XSessionConfigObject] = namespace_objs.x_session_config_objects
                # Remove duplicates according to pid
                session_details_dict = {x_session_config.pid: x_session_config
                                        for x_session_config in x_session_config_objects}
                x_session_config_objects = list(session_details_dict.values())
                if self.session_filters is not None:
                    for session_filter in self.session_filters:
                        if session_filter is None:
                            continue
                        x_session_config_objects[:] = session_filter(x_session_config_objects)

                if len(x_session_config_objects) == 0:
                    print('No application to restore.')
                    print('Done!')
                    return

                def restore_sessions_async(_x_session_config_objects_copy: List[XSessionConfigObject]):
                    t = threading.Thread(target=self._restore_sessions,
                                         args=(session_name,
                                               restoring_interval,
                                               _x_session_config_objects_copy,
                                               ))
                    t.start()
                    return t

                x_session_config_objects_copy = copy.deepcopy(x_session_config_objects)
                for x_session_config_object in x_session_config_objects_copy:
                    x_session_config_object.pid = None

                max_desktop_number = self._get_max_desktop_number(x_session_config_objects)
                with self.create_enough_workspaces(max_desktop_number):
                    x_session_config_objects_copy.sort(key=attrgetter('memory_percent'), reverse=True)
                    restore_thread = restore_sessions_async(x_session_config_objects_copy)
                    restore_thread.join()
                print('Done!')

    def _restore_sessions(self,
                          session_name,
                          restoring_interval,
                          _x_session_config_objects_copy: List[XSessionConfigObject]):
        self._suppress_log_if_already_in_workspace = True
        self._if_restore_geometry = True

        failed_restores = []
        succeeded_restores = []
        for index, namespace_obj in enumerate(_x_session_config_objects_copy):
            cmd: list = namespace_obj.cmd
            app_name: str = namespace_obj.app_name
            try:
                print('Restoring application:              [%s]' % app_name)
                if len(cmd) == 0:
                    so = suppress_output.SuppressOutput(True, True)
                    with so.suppress_output():
                        launched = gio_utils.GDesktopAppInfo().launch_app(app_name)
                        if not launched:
                            print('Failure to restore the application named %s '
                                  'due to empty commandline [%s]'
                                  % (app_name, str(cmd)))
                    continue

                namespace_obj.cmd = [c for c in cmd if c != "--gapplication-service"]
                try:
                    process = subprocess_utils.run_cmd(namespace_obj.cmd)
                    namespace_obj.pid = process.pid
                    succeeded_restores.append(index)
                    self.move_window(session_name)
                    # print('Success to restore application:     [%s]' % app_name)

                    # Wait some time, in case of freezing the entire system
                    sleep(restoring_interval)
                except FileNotFoundError as fnfe:
                    launched = False
                    part_cmd = namespace_obj.cmd[0]
                    # Check if this is a Snap application
                    snapd = snapd_workaround.Snapd()
                    is_snap_app, snap_app_name = snapd.is_snap_app(part_cmd)
                    if is_snap_app:
                        print('%s is a Snap app' % app_name)
                        launched = snapd.launch([snap_app_name])

                    if not launched:
                        launched = gio_utils.GDesktopAppInfo().launch_app(app_name)

                    if not launched:
                        raise fnfe
                    else:
                        self.move_window(session_name)
                        print('%s launched' % app_name)
            except Exception as e:
                failed_restores.append(index)
                print(traceback.format_exc())
                print('Failure to restore the application named %s due to the previous error' % app_name)

        _x_session_config_objects_copy[:] = [o for index, o in enumerate(_x_session_config_objects_copy)
                                             if index not in failed_restores]

        # Retry about 2 minutes
        retry_count_down = 60
        while retry_count_down > 0:
            retry_count_down = retry_count_down - 1
            sleep(1.5)
            # xsm = XSessionManager(self.session_filters)
            # xsm._suppress_log_if_already_in_workspace = True
            # xsm.move_window(session_name)
            self._suppress_log_if_already_in_workspace = True
            self.move_window(session_name)

    @contextmanager
    def create_enough_workspaces(self, max_desktop_number: int):
        # Create enough workspaces
        if wnck_utils.is_gnome():
            workspace_count = wnck_utils.get_workspace_count()
            if workspace_count >= max_desktop_number:
                yield
                return

            gsettings = gio_utils.GSettings(access_dynamic_workspaces=True, access_num_workspaces=True)
            if gsettings.is_dynamic_workspaces():
                gsettings.disable_dynamic_workspaces()
                try:
                    gsettings.set_workspaces_number(max_desktop_number)
                    try:
                        yield
                    finally:
                        gsettings.enable_dynamic_workspaces()
                except Exception as e:
                    import traceback
                    print(traceback.format_exc())
            else:
                workspaces_number = gsettings.get_workspaces_number()
                if max_desktop_number > workspaces_number:
                    gsettings.set_workspaces_number(max_desktop_number)
                yield
        else:
            yield

    def close_windows(self, including_apps_with_multiple_windows: bool = False):
        sessions: List[XSessionConfigObject] = \
            self.get_session_details(remove_duplicates_by_pid=False,
                                     session_filters=self.session_filters).x_session_config_objects

        if len(sessions) == 0:
            print('No application to close.')
            return

        sessions.sort(key=attrgetter('pid'))
        for pid, group_by_pid in groupby(sessions, key=attrgetter('pid')):
            a_process_with_many_windows: List[XSessionConfigObject] = list(group_by_pid)
            if len(a_process_with_many_windows) > 1:
                if including_apps_with_multiple_windows:
                    a_process_with_many_windows.sort(key=attrgetter('window_id'), reverse=True)
                    # Close one application's windows one by one from the last one
                    for session in a_process_with_many_windows:
                        print('Closing %s(%s %s).' % (session.app_name, session.window_id, session.pid))
                        wnck_utils.close_window_gracefully_async(session.window_id_the_int_type)
            else:
                session = a_process_with_many_windows[0]
                print('Closing %s(%s %s).' % (session.app_name, session.window_id, session.pid))
                wnck_utils.close_window_gracefully_async(session.window_id_the_int_type)

            # Wait some time, in case of freezing the entire system
            sleep(0.25)

    def move_window(self, session_name):
        session_path = Path(self.base_location_of_sessions, session_name)
        if not session_path.exists():
            raise FileNotFoundError('Session file [%s] was not found.' % session_path)

        with open(session_path, 'r') as file:
            namespace_objs: XSessionConfig = json.load(file, object_hook=lambda d: Namespace(**d))

        x_session_config_objects: List[XSessionConfigObject] = namespace_objs.x_session_config_objects
        x_session_config_objects.sort(key=attrgetter('desktop_number'))

        if self.session_filters is not None:
            for session_filter in self.session_filters:
                if session_filter is None:
                    continue
                x_session_config_objects[:] = session_filter(x_session_config_objects)

        if len(x_session_config_objects) == 0:
            print('No application to move.')
            return

        max_desktop_number = self._get_max_desktop_number(x_session_config_objects)
        with self.create_enough_workspaces(max_desktop_number):
            for namespace_obj in x_session_config_objects:
                try:
                    self._move_window(namespace_obj, need_retry=False)
                except:  # Catch all exceptions to be able to restore other apps
                    import traceback
                    print(traceback.format_exc())

        # Some apps may not be launched successfully due to any possible reason
        # if len(self._windows_can_not_be_moved) > 0:
        #     print('Those windows cannot be moved: ')
        #     for w in self._windows_can_not_be_moved:
        #         print(w)

    def _get_max_desktop_number(self, x_session_config_objects):
        return max([x_session_config_object.desktop_number
                    for x_session_config_object in x_session_config_objects]) + 1

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['_moving_windows_pool']
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)

    def _move_window_async(self, namespace_obj: XSessionConfigObject, pid: int = None):
        self._moving_windows_pool.apply_async(
            retry.Retry(6, 1).do_retry(self._move_window, (namespace_obj, pid)))

    def _move_window(self, saved_window: XSessionConfigObject, pid: int = None, need_retry=True):
        try:
            desktop_number = saved_window.desktop_number
            if hasattr(saved_window, 'window_state'):
                saved_window_state = saved_window.window_state
            else:
                saved_window_state = None

            pids = []
            if pid:
                pids = [c.pid for c in psutil.Process(pid).children()]
                pids.append(pid)

            # Get process info according to command line
            if len(pids) == 0:
                cmd = saved_window.cmd
                if len(cmd) <= 0:
                    return

                for p in psutil.process_iter(attrs=['pid', 'cmdline']):
                    if len(p.cmdline()) <= 0:
                        continue

                    if self._is_same_cmd(p, cmd):
                        pids.append(p.pid)
                        # break

            if len(pids) == 0:
                self._windows_can_not_be_moved.append(saved_window)
                return

            no_need_to_move = True
            moving_windows = []
            try:
                running_windows = wmctl_wrapper.get_running_windows()
            except CalledProcessError:
                # Try again. Handle the error of 'X Error of failed request:  BadWindow (invalid Window parameter)'
                sleep(0.25)
                running_windows = wmctl_wrapper.get_running_windows()

            x_session_config: XSessionConfig = XSessionConfigObject.convert_wmctl_result_2_list(running_windows, False)
            x_session_config_objects: List[XSessionConfigObject] = x_session_config.x_session_config_objects
            x_session_config_objects.sort(key=attrgetter('desktop_number'))

            # Used to calculate the number of windows of an app
            counter: collections.Counter = collections.Counter(s.pid for s in x_session_config_objects)

            for running_window in x_session_config_objects:
                if running_window.pid in pids:
                    no_need_to_compare_title = (counter[running_window.pid] == 1)
                    if no_need_to_compare_title or\
                            self._is_same_window(running_window,
                                                 saved_window):
                        if running_window.desktop_number == int(desktop_number):
                            self._restore_geometry(saved_window)
                            self.fix_window_state(saved_window_state, running_window.window_id_the_int_type)
                            if not self._suppress_log_if_already_in_workspace:
                                print('"%s" has already been in Workspace %s' % (running_window.window_title,
                                                                                 desktop_number))
                                # Record windows which are in it's Workspace already, so that we don't handle it later.
                                if running_window.window_id not in self._moved_windowids_cache:
                                    self._moved_windowids_cache.append(running_window.window_id)
                            continue
                        moving_windows.append(running_window)
                        no_need_to_move = False
                        # break
                else:
                    no_need_to_move = False

            if need_retry and len(moving_windows) == 0:
                raise retry.NeedRetryException(saved_window)
            elif no_need_to_move:
                return

            for running_window in moving_windows:
                running_window_id = running_window.window_id
                window_id_the_int_type = running_window.window_id_the_int_type
                if running_window_id in self._moved_windowids_cache:
                    self._restore_geometry(saved_window)
                    self.fix_window_state(saved_window_state, window_id_the_int_type)
                    continue
                window_title = running_window.window_title
                if string_utils.empty_string(window_title):
                    window_title = wnck_utils.get_app_name(window_id_the_int_type)
                print('Moving window to desktop:           [%s : %s]' % (window_title, desktop_number))
                # wmctl_wrapper.move_window_to(running_window_id, str(desktop_number))
                is_sticky = wnck_utils.is_sticky(window_id_the_int_type)
                wnck_utils.move_window_to(window_id_the_int_type, desktop_number)
                # Wait some time for processing event completely, no guarantee though
                sleep(0.25)

                self._moved_windowids_cache.append(running_window_id)
                self.fix_window_state(saved_window_state, window_id_the_int_type)
                if not wnck_utils.is_sticky(window_id_the_int_type) and is_sticky:
                    wnck_utils.stick(window_id_the_int_type)

                self._restore_geometry(saved_window)

        except retry.NeedRetryException as ne:
            raise ne
        except Exception as e:
            import traceback
            print(traceback.format_exc())

    def _restore_geometry(self, x_session_config_object: XSessionConfigObject):
        if self._if_restore_geometry is False:
            return

        window_position = x_session_config_object.window_position
        if hasattr(window_position, 'provider'):
            provider = window_position.provider
            if provider == 'Wnck':
                x_offset = window_position.x_offset
                y_offset = window_position.y_offset
                width = window_position.width
                height = window_position.height
                wnck_utils.set_geometry(x_session_config_object.window_id_the_int_type,
                                        x_offset,
                                        y_offset,
                                        width,
                                        height)

    def fix_window_state(self,
                         window_state: XSessionConfigObject.WindowState,
                         window_id_the_int_type: int):
        if window_state:
            if window_state.is_sticky:
                wnck_utils.stick(window_id_the_int_type)
            if window_state.is_above:
                wnck_utils.make_above(window_id_the_int_type)

    def _is_same_window(self, window1: XSessionConfigObject, window2: XSessionConfigObject):
        # Deal with JetBrains products. Move the window if they are the same project.
        app_name1 = wnck_utils.get_app_name(window1.window_id_the_int_type)
        app_name2 = window2.app_name
        if app_name1 == app_name2 and app_name1.startswith('jetbrains-'):
            return window1.window_title.split(' ')[0] == window2.window_title.split(' ')[0]

        if window1.window_title == window2.window_title:
            return True

        return False

    def _is_same_cmd(self, p: psutil.Process, second_cmd: List):
        first_cmdline = [c for c in p.cmdline() if (c != "--gapplication-service" and not c.startswith('--pid='))]
        second_cmd = [c for c in second_cmd if (c != "--gapplication-service" and not c.startswith('--pid='))]
        if len(first_cmdline) <= 0 or len(second_cmd) <= 0:
            return

        first_one_is_snap_app, first_snap_app_name = snapd_workaround.Snapd.is_snap_app(first_cmdline[0])
        if first_one_is_snap_app:
            second_one_also_is_snap_app, second_snap_app_name = snapd_workaround.Snapd.is_snap_app(second_cmd[0])
            if second_one_also_is_snap_app:
                return first_snap_app_name == second_snap_app_name

        return first_cmdline == second_cmd

