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
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

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

    def __init__(self, 
                 verbose: bool=False,
                 vv: bool=False,
                 session_filters: List[SessionFilter]=None,
                 base_location_of_sessions: str=Locations.BASE_LOCATION_OF_SESSIONS,
                 base_location_of_backup_sessions: str=Locations.BASE_LOCATION_OF_BACKUP_SESSIONS):
        self.session_filters = session_filters
        self.base_location_of_sessions = base_location_of_sessions
        self.base_location_of_backup_sessions = base_location_of_backup_sessions

        self._moved_windowids_cache = []
        self._suppress_log_if_already_in_workspace = False
        self.opened_window_id_pid: Dict[int, List[int]] = {}
        self.opened_window_id_pid_old: Dict[int, List[int]] = {}

        self._windows_can_not_be_moved: List[XSessionConfigObject] = []
        self._restore_geometry_or_not = False
        self.verbose = verbose
        self.vv = vv
        self.restore_app_countdown = -1

        self.instance_lock = threading.Lock()

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
        
        if self.vv:
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
        if self.vv:
            print('Got the running process list according to wmctl: %s' % json.dumps(x_session_config, default=lambda o: o.__dict__))
        x_session_config_objects: List[XSessionConfigObject] = x_session_config.x_session_config_objects
        counter: collections.Counter = collections.Counter(window.pid for window in x_session_config_objects)
        for idx, sd in enumerate(x_session_config_objects):
            try:
                process = psutil.Process(sd.pid)
                sd.username = process.username()
                sd.cmd = process.cmdline()
                sd.process_create_time = datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
                sd.cpu_percent = process.cpu_percent()
                sd.memory_percent = process.memory_percent()
            except psutil.NoSuchProcess as e:
                if self.verbose:
                    print('Failed to get process [%s] info using psutil due to: %s' % (sd, str(e)))
                sd.username = ''
                sd.cmd = []
                sd.process_create_time = None
                sd.cpu_percent = 0.0
                sd.memory_percent = 0.0
                
            sd.app_name = wnck_utils.get_app_name(sd.window_id_the_int_type)
            sd.window_state = sd.WindowState()
            sd.window_state.is_above = wnck_utils.is_above(sd.window_id_the_int_type)
            sd.window_state.is_sticky = wnck_utils.is_sticky(sd.window_id_the_int_type)
            sd.windows_count = counter[sd.pid]
            
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

        if session_filters:
            for session_filter in session_filters:
                if session_filter is None:
                    continue
                x_session_config.x_session_config_objects[:] = \
                    session_filter(x_session_config.x_session_config_objects)

        if self.vv:
            print('Completed the running process list and applied filters: %s' %
                  json.dumps(x_session_config, default=lambda o: o.__dict__))
        return x_session_config

    def backup_session(self, original_session_path):
        backup_time = datetime.datetime.fromtimestamp(time())
        with open(original_session_path, 'r') as file:
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

    def restore_session(self, session_name, restoring_interval=0.5):
        session_path = Path(self.base_location_of_sessions, session_name)
        if not session_path.exists():
            raise FileNotFoundError('Session file [%s] was not found.' % session_path)

        with open(session_path, 'r') as file:
            print('Restoring session located [%s] ' % session_path)
            namespace_objs: XSessionConfig = json.load(file, object_hook=lambda d: Namespace(**d))
            # Note: os.fork() does not support MS Windows
            pid = os.fork()
            # Launch APPs in the child process
            if pid == 0:
                x_session_config_objects: List[XSessionConfigObject] = namespace_objs.x_session_config_objects
                # Remove duplicates according to pid
                session_details_dict = {x_session_config.pid: x_session_config
                                        for x_session_config in x_session_config_objects}
                x_session_config_objects = list(session_details_dict.values())
                if self.session_filters:
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
                with wnck_utils.create_enough_workspaces(max_desktop_number):
                    x_session_config_objects_copy.sort(key=attrgetter('memory_percent'), reverse=True)
                    self.restore_app_countdown = len(x_session_config_objects_copy)
                    restore_thread = restore_sessions_async(x_session_config_objects_copy)
                    restore_thread.join()
                    self._move_windows_while_restore(session_name, x_session_config_objects_copy)
                print('Done!')

    def _move_windows_while_restore(self, session_name, x_session_config_objects_copy: List[XSessionConfigObject]):
        retry_count_down = self.calculate_retry_count_down(x_session_config_objects_copy)
        # Retry some minutes
        while retry_count_down > 0:
            # handle pending events
            while Gtk.events_pending():
                Gtk.main_iteration()

            retry_count_down = retry_count_down - 1

            self._suppress_log_if_already_in_workspace = True
            self.move_window(session_name)

            with self.instance_lock:
                if self.restore_app_countdown <= 0:
                    break
            
    def calculate_retry_count_down(self, _x_session_config_objects_copy: List[XSessionConfigObject]) -> int:
        retry_count_down = 15
        if not _x_session_config_objects_copy:
            retry_count_down = 1
        else:
            max_windows_count_app = max(_x_session_config_objects_copy, key=lambda x: x.windows_count 
                                                    if hasattr(x, 'windows_count') else -1)
            if hasattr(max_windows_count_app, 'windows_count') \
                    and max_windows_count_app.windows_count == 1:
                retry_count_down = 5
        if self.verbose:
            print('Calculated retry_count_down: %d' % retry_count_down)
        return retry_count_down
        
    def _restore_sessions(self,
                          session_name,
                          restoring_interval,
                          _x_session_config_objects_copy: List[XSessionConfigObject]):
        self._suppress_log_if_already_in_workspace = True
        self._restore_geometry_or_not = True

        running_restores = []
        failed_restores = []
        succeeded_restores = []
        running_session: XSessionConfig = self.get_session_details(remove_duplicates_by_pid=False, 
                                                                   session_filters=self.session_filters);
        for index, namespace_obj in enumerate(_x_session_config_objects_copy):
            cmd: list = namespace_obj.cmd
            app_name: str = namespace_obj.app_name
            try:
                is_running = False
                for running_window in running_session.x_session_config_objects:
                    if self._is_same_app(running_window, namespace_obj) \
                            and self._is_same_cmd(running_window.cmd, cmd):
                        print('%s is running in Workspace %d, skip...' % (app_name, running_window.desktop_number))
                        namespace_obj.pid = running_window.pid
                        running_restores.append(index)
                        is_running = True
                        with self.instance_lock:
                            self.restore_app_countdown = self.restore_app_countdown - 1
                        break
                if is_running:
                    continue
                
                print('Restoring application:              [%s]' % app_name)
                app_info = gio_utils.GDesktopAppInfo()
                if len(cmd) == 0:
                    def launched_callback(cb_data):
                        namespace_obj.pid = cb_data['pid']
                    launched = app_info.launch_app(app_name, launched_callback)
                    if not launched:
                        print('Failure to restore the application named %s '
                              'due to empty commandline [%s]'
                              % (app_name, str(cmd))) 
                    else:
                        sleep(restoring_interval)
                        if self.verbose:
                            print('%s launched' % app_name)
                    self.move_window(session_name)
                    continue

                launched = False
                try:
                    namespace_obj.cmd = [c for c in cmd if c != "--gapplication-service"]
                    process = subprocess_utils.launch_app(namespace_obj.cmd)
                    namespace_obj.pid = process.pid
                    succeeded_restores.append(index)
                    launched = True
                except FileNotFoundError as fnfe:
                    def launched_callback(cb_data):
                        namespace_obj.pid = cb_data['pid']

                    part_cmd = namespace_obj.cmd[0]
                    # Check if this is a Snap application
                    snapd = snapd_workaround.Snapd()
                    is_snap_app, snap_app_name = snapd.is_snap_app(part_cmd)
                    if is_snap_app:
                        print('%s is a Snap app' % app_name)
                        launched = snapd.launch_app([snap_app_name], launched_callback)

                    if not launched:
                        print('Searching %s ...' % app_name)
                        launched = app_info.launch_app(app_name, launched_callback)

                    if not launched:
                        raise fnfe

                if launched:
                    if self.verbose:
                        print('%s launched' % app_name)
                    sleep(restoring_interval)
                    if index == len(_x_session_config_objects_copy) - 1 \
                            or index % 3 == 0: # move windows while every 3 apps launched
                        self.move_window(session_name)

            except Exception as e:
                failed_restores.append(index)
                print(traceback.format_exc())
                print('Failure to restore the application named %s due to the previous error' % app_name)

        _x_session_config_objects_copy[:] = [o for index, o in enumerate(_x_session_config_objects_copy)
                                             if index not in failed_restores + running_restores]

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
                # Do not close the app with more than one windows
                if not including_apps_with_multiple_windows:
                    continue

                a_process_with_many_windows.sort(key=attrgetter('window_id'), reverse=True)
                # Close one application's windows one by one, starting with the most top one
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

        if self.session_filters:
            for session_filter in self.session_filters:
                if session_filter is None:
                    continue
                x_session_config_objects[:] = session_filter(x_session_config_objects)

        if len(x_session_config_objects) == 0:
            print('No application to move.')
            return

        max_desktop_number = self._get_max_desktop_number(x_session_config_objects)
        with wnck_utils.create_enough_workspaces(max_desktop_number):
            for namespace_obj in x_session_config_objects:
                try:
                    self._move_window(namespace_obj, need_retry=False)
                except:  # Catch all exceptions to be able to restore other apps
                    import traceback
                    print(traceback.format_exc())

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
                    try:
                        cmdline: list = p.cmdline()
                    except:
                        # Eat all exceptions raised here, a process could exist a short while
                        continue

                    if len(cmdline) <= 0:
                        continue

                    if self._is_same_cmd(cmdline, cmd):
                        pids.append(p.pid)

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
        if not self._restore_geometry_or_not:
            return

        window_position = x_session_config_object.window_position
        if not hasattr(window_position, 'provider'):
            return

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

    def _is_same_app(self, running_window1: XSessionConfigObject, window2: XSessionConfigObject):
        app_name1 = wnck_utils.get_app_name(running_window1.window_id_the_int_type)
        app_name2 = window2.app_name
        if string_utils.empty_string(app_name1) \
                or string_utils.empty_string(app_name2):
            return False
        return app_name1 == app_name2
    
    def _is_same_window(self, running_window1: XSessionConfigObject, window2: XSessionConfigObject):
        # Deal with JetBrains products. Move the window if they are the same project.
        app_name1 = wnck_utils.get_app_name(running_window1.window_id_the_int_type)
        app_name2 = window2.app_name
        if app_name1 == app_name2 and app_name1.startswith('jetbrains-'):
            return running_window1.window_title.split(' ')[0] == window2.window_title.split(' ')[0]

        if running_window1.window_title == window2.window_title:
            return True

        return False

    def _is_same_cmd(self, first_cmdline: List, second_cmd: List):
        # Remove consecutive duplicates
        # The args could be duplicated in some apps, like Chromium-based browsers, such as Microsoft Edge 96.0.1054.43, eg: msedge --enable-crashpad --enable-crashpad
        first_cmdline = [c[0] for c in groupby(first_cmdline) if (c[0] != "--gapplication-service" and not c[0].startswith('--pid='))]
        second_cmd = [c[0] for c in groupby(second_cmd) if (c[0] != "--gapplication-service" and not c[0].startswith('--pid='))]
        if len(first_cmdline) == 0 and len(second_cmd) == 0:
            return True
        
        if len(first_cmdline) <= 0 or len(second_cmd) <= 0:
            return False

        first_one_is_snap_app, first_snap_app_name = snapd_workaround.Snapd.is_snap_app(first_cmdline[0])
        if first_one_is_snap_app:
            second_one_also_is_snap_app, second_snap_app_name = snapd_workaround.Snapd.is_snap_app(second_cmd[0])
            if second_one_also_is_snap_app:
                return first_snap_app_name == second_snap_app_name

        return first_cmdline == second_cmd

