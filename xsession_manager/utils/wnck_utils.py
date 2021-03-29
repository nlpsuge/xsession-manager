# Note: Wnck may not works in Wayland
import threading
from time import time

import gi

gi.require_version('Wnck', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Wnck, Gtk


class WnckUtils:

    # Add this variable to avoid:
    # (xsm:247715): Wnck-CRITICAL **: 16:24:43.212: update_client_list: assertion 'reentrancy_guard == 0' failed
    # when calling 'self.screen.force_update()' in the __init_() method
    screen_force_updated = False

    screen: Wnck.Screen = None

    def __init__(self, screen_force_update: bool=True):
        # Use a lock to handle race conditions
        lock = threading.Lock()
        with lock:
            if self.screen is None:
                self.screen: Wnck.Screen = Wnck.Screen.get_default()

            if screen_force_update and not self.screen_force_updated:
                # In case that cannot get the Wnck.Workspace instance
                # while Gtk.events_pending():
                #     Gtk.main_iteration()
                self.screen.force_update()
                self.screen_force_updated = True

    def close_window_gracefully_async(self, window_id: int):
        window: Wnck.Window = self.get_window(window_id)
        # window may be None if this window has been closed by the user
        if window:
            window.close(time())

    def move_window_to(self, window_id, desktop_number):
        ws = self.screen.get_workspace(desktop_number)
        if ws is None:
            print('Workspace %d not found!' % desktop_number)
        else:
            window: Wnck.Window = self.get_window(window_id)
            if window is None:
                # Not sure why window is None sometimes
                return
            window.move_to_workspace(ws)

    def is_gnome(self) -> bool:
        wmn = self.screen.get_window_manager_name()
        if wmn == 'GNOME Shell':
            return True
        return False

    def get_workspace_count(self):
        return self.screen.get_workspace_count()

    def get_app_name(self, xid: int) -> str:
        window = self.get_window(xid)
        if window is None:
            return ''
        # See: https://developer.gnome.org/libwnck/stable/WnckWindow.html#wnck-window-get-class-group-name
        # See: https://tronche.com/gui/x/icccm/sec-4.html#WM_CLASS
        name = window.get_class_group_name()
        if name == 'Wine':  # eg: https://snapcraft.io/notepad-plus-plus
            # Return a reasonable name
            return window.get_class_instance_name()
        return name

    def get_window(self, xid: int) -> Wnck.Window:
        window: Wnck.Window = Wnck.Window.get(xid)
        return window

    def get_window_title(self, xid: int) -> str:
        window = self.get_window(xid)
        return window.get_name()

    def is_sticky(self, xid: int) -> bool:
        window: Wnck.Window = Wnck.Window.get(xid)
        return window.is_sticky()

    def count_windows(self, xid: int) -> int:
        window: Wnck.Window = Wnck.Window.get(xid)
        # Windows may not open yet
        if window is None:
            return -1

        app: Wnck.Application = window.get_application()
        return app.get_n_windows()

    def get_windows(self):
        return self.screen.get_windows()
